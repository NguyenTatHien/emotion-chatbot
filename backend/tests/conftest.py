import pytest
from fastapi.testclient import TestClient

from app import registry
from app.config import reload_settings
from app.constants import MODULE_NAMES
from app.main import app
from app.session import store

_ENV_KEYS = [
    "MODEL_MODE",
    "MOCK_LATENCY_MS",
    "HISTORY_TURNS",
    "SAFETY_HOTLINE_TEXT",
    "CORS_ORIGINS",
    "LLM_TIMEOUT",
    "EMOTION_TIMEOUT",
    "SAFETY_TIMEOUT",
    "MUSIC_TIMEOUT",
    "MAX_AUDIO_MB",
    *[f"{n.upper()}_MODE" for n in MODULE_NAMES],
]


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Mỗi test bắt đầu với cấu hình mặc định, phiên rỗng và không có override."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    reload_settings()
    store.clear()
    registry.reset_overrides()
    yield
    registry.reset_overrides()
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
