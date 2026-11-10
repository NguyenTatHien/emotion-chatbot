"""Khung model server `colab/server_app.py` chạy với mock."""

import importlib.util
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVER_FILE = Path(__file__).resolve().parents[3] / "colab" / "server_app.py"
LABELS = {"Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise"}
H = {"X-Model-Server-Token": "tok"}


def load_server(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location(f"server_app_{uuid.uuid4().hex}", SERVER_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_app()


@pytest.fixture
def server(monkeypatch):
    app = load_server(monkeypatch, SERVER_USE_MOCKS="1", MODEL_SERVER_TOKEN="tok")
    with TestClient(app) as c:
        yield c


def test_health_needs_no_token(server):
    body = server.get("/health").json()
    assert body["ok"] is True and body["modules"] == ["emotion", "speech", "llm"]


def test_missing_or_wrong_token_is_401(server):
    assert server.post("/emotion", json={"text": "x"}).status_code == 401
    r = server.post("/emotion", json={"text": "x"}, headers={"X-Model-Server-Token": "sai"})
    assert r.status_code == 401


def test_no_token_required_when_unset(monkeypatch):
    monkeypatch.delenv("MODEL_SERVER_TOKEN", raising=False)
    with TestClient(load_server(monkeypatch, SERVER_USE_MOCKS="1")) as c:
        assert c.post("/emotion", json={"text": "x"}).status_code == 200


def test_routes_return_mock_data(server, audio_samples):
    emo = server.post("/emotion", json={"text": "vui quá"}, headers=H).json()
    assert emo["label"] in LABELS
    wav = ("a.wav", audio_samples["wav"], "audio/wav")
    assert server.post("/transcribe", files={"file": wav}, headers=H).json()["text"]
    assert server.post("/prosody", files={"file": wav}, headers=H).json()["arousal"] == "medium"
    gen = server.post(
        "/generate",
        json={"text": "buồn", "emotion": emo, "arousal": None, "history": [], "goal": None},
        headers=H,
    ).json()
    assert gen["reply"]


def test_unimplemented_real_module_returns_501(monkeypatch):
    """Không đặt SERVER_USE_MOCKS: module thật còn là stub thì trả 501, không phải 500.

    Gắn một stub vào modules.speech để test không phụ thuộc việc module thật đã có code
    hay chưa (và không cần cài thư viện ML).
    """
    monkeypatch.delenv("SERVER_USE_MOCKS", raising=False)
    monkeypatch.delenv("MODEL_SERVER_TOKEN", raising=False)
    from modules import speech

    def stub(_wav_path: str) -> str:
        raise NotImplementedError("chưa cài đặt")

    monkeypatch.setattr(speech, "transcribe", stub)
    with TestClient(load_server(monkeypatch)) as c:
        r = c.post("/transcribe", files={"file": ("a.wav", b"RIFF", "audio/wav")})
        assert r.status_code == 501
        assert "chưa cài đặt" in r.json()["detail"]
