"""POST /api/chat với audio_file thật (sinh bằng ffmpeg): chuẩn hoá, giới hạn, dự phòng."""

import tempfile
import time
import wave
from pathlib import Path

import pytest

from app import audio, registry

AUDIO_DIRS = ("chat_audio_*", "chat_wav_*")
LABELS = ("Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise")


def _temp_dirs() -> set[Path]:
    root = Path(tempfile.gettempdir())
    return {p for pattern in AUDIO_DIRS for p in root.glob(pattern)}


def _raise_missing():
    raise audio.AudioToolMissing("không có ffmpeg")


def post_audio(client, data: bytes, name: str = "voice.webm", **fields):
    return client.post(
        "/api/chat",
        data={"session_id": "s1", **fields},
        files={"audio_file": (name, data, "application/octet-stream")},
    )


@pytest.fixture
def spy_speech():
    """Bắt đường dẫn WAV mà transcribe/extract_prosody nhận được."""
    seen: dict = {"paths": [], "headers": []}

    def inspect(path):
        seen["paths"].append(path)
        with wave.open(path, "rb") as w:
            seen["headers"].append((w.getnchannels(), w.getframerate(), w.getsampwidth()))

    def transcribe(path):
        inspect(path)
        return "hôm nay mệt quá"

    def prosody(path):
        inspect(path)
        return {"arousal": "high"}

    registry.override("speech", transcribe, "transcribe")
    registry.override("speech", prosody, "extract_prosody")
    return seen


@pytest.mark.parametrize(
    ("kind", "filename"),
    [("webm", "voice.webm"), ("ogg", "voice.ogg"), ("m4a", "voice.m4a"), ("wav", "voice.wav")],
)
def test_formats_are_normalized_to_wav_16k_mono(client, audio_samples, spy_speech, kind, filename):
    before = _temp_dirs()
    r = post_audio(client, audio_samples[kind], filename)
    assert r.status_code == 200
    assert r.json()["transcript"] == "hôm nay mệt quá"
    assert len(spy_speech["paths"]) == 2
    assert spy_speech["paths"][0] == spy_speech["paths"][1]
    # 1 kênh, 16 kHz, 16-bit
    assert spy_speech["headers"] == [(1, 16000, 2)] * 2
    # Thư mục tạm của lượt này đã bị xoá.
    assert not Path(spy_speech["paths"][0]).exists()
    assert _temp_dirs() - before == set()


def test_arousal_reaches_response_and_modules(client, audio_samples, spy_speech):
    seen = {}

    def llm(text, emotion, arousal, history, goal=None):
        seen["llm"] = arousal
        return "mình nghe bạn?"

    def music(label, arousal, goal=None, k=5):
        seen["music"] = arousal
        return []

    registry.override("llm", llm)
    registry.override("music", music)
    body = post_audio(client, audio_samples["webm"]).json()
    assert body["emotion"]["arousal"] == "high"
    assert seen == {"llm": "high", "music": "high"}


def test_message_and_audio_together(client, audio_samples, spy_speech):
    texts = []

    def emotion(text):
        texts.append(text)
        return {"label": "Other", "probs": {k: 1 / 7 for k in LABELS}}

    registry.override("emotion", emotion)
    body = post_audio(client, audio_samples["webm"], message="A").json()
    assert texts == ["A"]
    assert body["transcript"] == "hôm nay mệt quá"


def test_audio_too_long_returns_413(client, audio_samples):
    before = _temp_dirs()
    r = post_audio(client, audio_samples["long_wav"], "long.wav")
    assert r.status_code == 413
    assert "30" in r.json()["detail"]
    assert _temp_dirs() - before == set()


def test_audio_too_heavy_never_reaches_pipeline(client, set_env, monkeypatch):
    set_env(MAX_AUDIO_MB=1)
    called = []

    async def boom(*a, **k):
        called.append(1)
        raise AssertionError("pipeline không được gọi")

    monkeypatch.setattr("app.pipeline.handle_chat", boom)
    r = post_audio(client, b"\0" * (6 * 1024 * 1024), "big.webm")
    assert r.status_code == 413
    assert called == []


def test_text_file_named_webm_returns_415(client, audio_samples):
    before = _temp_dirs()
    r = post_audio(client, audio_samples["text"], "a.webm")
    assert r.status_code == 415
    assert r.json()["detail"]
    assert _temp_dirs() - before == set()


def test_transcribe_error_uses_transcript_hint(client, audio_samples):
    def broken(path):
        raise RuntimeError("PhoWhisper hỏng")

    registry.override("speech", broken, "transcribe")
    texts = []
    original = registry.get("emotion")

    def emotion(text):
        texts.append(text)
        return original(text)

    registry.override("emotion", emotion)
    body = post_audio(client, audio_samples["webm"], transcript_hint="mình hơi lo").json()
    assert texts == ["mình hơi lo"]
    assert body["transcript"] == "mình hơi lo"
    assert body["meta"]["degraded"] is True
    assert any("transcribe" in w for w in body["meta"]["warnings"])


def test_empty_transcript_uses_hint(client, audio_samples):
    registry.override("speech", lambda path: "   ", "transcribe")
    body = post_audio(client, audio_samples["webm"], transcript_hint="mình hơi lo").json()
    assert body["transcript"] == "mình hơi lo"
    assert body["meta"]["degraded"] is True


def test_transcribe_error_without_hint_returns_400(client, audio_samples):
    def broken(path):
        raise RuntimeError("hỏng")

    registry.override("speech", broken, "transcribe")
    r = post_audio(client, audio_samples["webm"])
    assert r.status_code == 400
    assert "gõ chữ" in r.json()["detail"]


def test_prosody_error_gives_null_arousal(client, audio_samples):
    def broken(path):
        raise RuntimeError("librosa hỏng")

    registry.override("speech", broken, "extract_prosody")
    body = post_audio(client, audio_samples["webm"]).json()
    assert body["emotion"]["arousal"] is None
    assert body["transcript"]
    assert body["meta"]["degraded"] is True
    assert any("prosody" in w for w in body["meta"]["warnings"])


def test_speech_runs_in_parallel(client, audio_samples):
    def slow(path):
        time.sleep(0.4)
        return "xin chào"

    def slow_prosody(path):
        time.sleep(0.4)
        return {"arousal": "low"}

    registry.override("speech", slow, "transcribe")
    registry.override("speech", slow_prosody, "extract_prosody")
    body = post_audio(client, audio_samples["webm"]).json()
    assert body["meta"]["latency_ms"] < 750


def test_missing_ffmpeg_degrades_to_hint(client, audio_samples, monkeypatch):
    monkeypatch.setattr(audio, "resolve_ffmpeg", _raise_missing)
    r = post_audio(client, audio_samples["webm"], transcript_hint="mình hơi lo")
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"] == "mình hơi lo"
    assert body["meta"]["degraded"] is True
    assert any("ffmpeg" in w for w in body["meta"]["warnings"])


def test_missing_ffmpeg_without_any_text_returns_400(client, audio_samples, monkeypatch):
    monkeypatch.setattr(audio, "resolve_ffmpeg", _raise_missing)
    assert post_audio(client, audio_samples["webm"]).status_code == 400


def test_missing_ffmpeg_with_message_still_answers(client, audio_samples, monkeypatch):
    monkeypatch.setattr(audio, "resolve_ffmpeg", _raise_missing)
    r = post_audio(client, audio_samples["webm"], message="mình buồn")
    assert r.status_code == 200
    assert r.json()["meta"]["degraded"] is True
