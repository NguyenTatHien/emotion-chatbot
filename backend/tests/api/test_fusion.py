"""Late fusion trong POST /api/chat: điều kiện áp dụng và kết quả đi xuống các bước sau."""

import pytest
from pydantic import ValidationError

from app import registry
from app.config import reload_settings

LABELS = ("Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise")


def probs_of(**values: float) -> dict[str, float]:
    return {k: values.get(k, 0.0) for k in LABELS}


FLIP = probs_of(Sadness=0.40, Anger=0.35, Other=0.25)


def post_audio(client, data: bytes, **fields):
    return client.post(
        "/api/chat",
        data={"session_id": "s1", **fields},
        files={"audio_file": ("voice.webm", data, "application/octet-stream")},
    )


def setup_voice(arousal, probs=FLIP, label="Sadness"):
    registry.override("speech", lambda path: "mình mệt quá", "transcribe")
    registry.override("speech", lambda path: {"arousal": arousal}, "extract_prosody")
    registry.override("emotion", lambda text: {"label": label, "probs": probs})


def test_text_only_has_no_fusion(client):
    registry.override("emotion", lambda text: {"label": "Sadness", "probs": FLIP})
    body = client.post("/api/chat", data={"session_id": "s1", "message": "mệt"}).json()
    assert body["meta"]["fusion_applied"] is False
    assert body["emotion"]["label_text"] is None
    assert body["emotion"]["probs_text"] is None


def test_medium_arousal_has_no_fusion(client, audio_samples):
    setup_voice("medium")
    body = post_audio(client, audio_samples["webm"]).json()
    assert body["meta"]["fusion_applied"] is False
    assert body["emotion"]["label"] == "Sadness"
    assert body["emotion"]["probs"] == FLIP
    assert body["emotion"]["label_text"] is None


def test_emotion_failure_has_no_fusion(client, audio_samples):
    setup_voice("high")

    def broken(text):
        raise RuntimeError("emotion hỏng")

    registry.override("emotion", broken)
    body = post_audio(client, audio_samples["webm"]).json()
    assert body["emotion"]["label"] == "Other"
    assert set(body["emotion"]["probs"].values()) == {1 / 7}
    assert body["meta"]["fusion_applied"] is False
    assert body["emotion"]["label_text"] is None


def test_alpha_zero_disables_fusion(client, audio_samples, set_env):
    set_env(FUSION_ALPHA=0)
    setup_voice("high")
    body = post_audio(client, audio_samples["webm"]).json()
    assert body["meta"]["fusion_applied"] is False
    assert body["emotion"]["label"] == "Sadness"
    assert body["emotion"]["probs"] == FLIP


def test_safety_turn_has_no_fusion(client, audio_samples):
    registry.override("speech", lambda path: "mình muốn chết", "transcribe")
    registry.override("speech", lambda path: {"arousal": "high"}, "extract_prosody")
    body = post_audio(client, audio_samples["webm"]).json()
    assert body["safety"] is True
    assert body["emotion"] is None
    assert body["meta"]["fusion_applied"] is False


def test_fused_label_reaches_music_llm_response_and_session(client, audio_samples):
    setup_voice("high")
    seen = {}

    def llm(text, emotion, arousal, history, goal=None):
        seen["llm"] = emotion
        return "mình nghe bạn."

    def music(label, arousal, goal=None, k=5, exclude=None):
        seen["music"] = label
        return []

    registry.override("llm", llm)
    registry.override("music", music)
    body = post_audio(client, audio_samples["webm"], goal="xoa_diu").json()

    assert body["meta"]["fusion_applied"] is True
    assert body["emotion"]["label"] == "Anger"
    assert body["emotion"]["label_text"] == "Sadness"
    assert body["emotion"]["probs_text"] == FLIP
    assert sum(body["emotion"]["probs"].values()) == pytest.approx(1.0)
    assert seen["music"] == "Anger"
    assert seen["llm"]["label"] == "Anger"
    assert seen["llm"]["probs"] == body["emotion"]["probs"]

    turn = client.get("/api/session/s1").json()["turns"][0]
    assert turn["emotion"]["label"] == "Anger"
    assert turn["emotion"]["label_text"] == "Sadness"
    assert turn["emotion"]["probs_text"] == FLIP


def test_fused_label_reaches_memory_notes(client, audio_samples):
    setup_voice("high")
    post_audio(client, audio_samples["webm"])
    seen = {}

    def llm(text, emotion, arousal, history, goal=None):
        seen["history"] = history
        return "ok"

    registry.override("llm", llm)
    client.post("/api/chat", data={"session_id": "s1", "message": "tiếp"})
    assert "Tức giận" in str(seen["history"])


def test_invalid_alpha_fails_config(monkeypatch):
    monkeypatch.setenv("FUSION_ALPHA", "0.9")
    with pytest.raises(ValidationError, match="FUSION_ALPHA"):
        reload_settings()
