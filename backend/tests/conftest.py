import subprocess

import pytest
from fastapi.testclient import TestClient

from app import registry
from app.clients import model_server
from app.config import reload_settings
from app.constants import MODULE_NAMES
from app.main import app
from app.session import store

_ENV_KEYS = [
    "MODEL_MODE",
    "MOCK_LATENCY_MS",
    "FUSION_ALPHA",
    "HISTORY_TURNS",
    "SAFETY_HOTLINE_TEXT",
    "CORS_ORIGINS",
    "LLM_TIMEOUT",
    "EMOTION_TIMEOUT",
    "SAFETY_TIMEOUT",
    "MUSIC_TIMEOUT",
    "MAX_AUDIO_MB",
    "MAX_AUDIO_SECONDS",
    "FFMPEG_BINARY",
    "SPEECH_TIMEOUT",
    "PROSODY_TIMEOUT",
    "MODEL_SERVER_URL",
    "MODEL_SERVER_TOKEN",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "ADMIN_TOKEN",
    "FEEDBACK_PATH",
    "REMOTE_TIMEOUT_EMOTION",
    "REMOTE_TIMEOUT_TRANSCRIBE",
    "REMOTE_TIMEOUT_PROSODY",
    "REMOTE_TIMEOUT_GENERATE",
    *[f"{n.upper()}_MODE" for n in MODULE_NAMES],
]


@pytest.fixture(autouse=True)
def clean_state(monkeypatch, tmp_path):
    """Mỗi test bắt đầu với cấu hình mặc định, phiên rỗng và không có override."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    # Không bao giờ ghi vào data/runtime/feedback.jsonl thật.
    monkeypatch.setenv("FEEDBACK_PATH", str(tmp_path / "feedback.jsonl"))
    reload_settings()
    store.clear()
    registry.reset_overrides()
    model_server.reset_state()
    yield
    registry.reset_overrides()
    model_server.reset_state()
    store.clear()
    monkeypatch.undo()
    reload_settings()


@pytest.fixture
def set_env(monkeypatch):
    """Đặt biến môi trường rồi nạp lại cấu hình."""

    def _set(**values):
        for key, value in values.items():
            monkeypatch.setenv(key, str(value))
        return reload_settings()

    return _set


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _make_audio(ffmpeg: str, out, seconds: float, *codec_args: str) -> bytes:
    subprocess.run(
        [
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}:sample_rate=48000",
            *codec_args, str(out),
        ],
        check=True,
        timeout=60,
    )  # fmt: skip
    return out.read_bytes()


@pytest.fixture(scope="session")
def audio_samples(tmp_path_factory) -> dict[str, bytes]:
    """Audio mẫu sinh bằng chính ffmpeg mà backend dùng (không commit file nhị phân)."""
    from app.audio import resolve_ffmpeg

    ffmpeg = resolve_ffmpeg()
    d = tmp_path_factory.mktemp("audio")
    return {
        "webm": _make_audio(ffmpeg, d / "s.webm", 5, "-c:a", "libopus"),
        "ogg": _make_audio(ffmpeg, d / "s.ogg", 3, "-c:a", "libopus"),
        "m4a": _make_audio(ffmpeg, d / "s.m4a", 3, "-c:a", "aac"),
        "wav": _make_audio(ffmpeg, d / "s.wav", 2, "-ac", "2", "-c:a", "pcm_s16le"),
        "long_wav": _make_audio(ffmpeg, d / "long.wav", 45, "-ac", "1", "-ar", "16000"),
        "text": "đây không phải audio\n".encode() * 50,
    }
