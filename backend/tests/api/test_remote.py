"""Chế độ remote: gọi model server qua HTTP (mock bằng respx, không có mạng thật)."""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.clients import model_server
from app.main import app, create_app

URL = "http://model.test"
PROBS = {
    "Anger": 0.01, "Disgust": 0.01, "Enjoyment": 0.02, "Fear": 0.8,
    "Other": 0.05, "Sadness": 0.1, "Surprise": 0.01,
}  # fmt: skip


@pytest.fixture
def remote(set_env):
    set_env(
        MODEL_SERVER_URL=URL,
        MODEL_SERVER_TOKEN="tok-123",
        EMOTION_MODE="remote",
        LLM_MODE="remote",
        SPEECH_MODE="remote",
    )


@pytest.fixture
def server():
    with respx.mock(base_url=URL, assert_all_called=False) as mock:
        yield mock


def chat(client, message="mình sợ lắm"):
    return client.post("/api/chat", data={"session_id": "s1", "message": message})


def test_remote_success(client, remote, server):
    emotion = server.post("/emotion").respond(200, json={"label": "Fear", "probs": PROBS})
    generate = server.post("/generate").respond(200, json={"reply": "Mình ở đây nghe bạn?"})
    body = chat(client).json()
    assert body["emotion"]["label"] == "Fear"
    assert body["reply"] == "Mình ở đây nghe bạn?"
    assert body["meta"]["modules"]["emotion"] == "remote"
    assert body["meta"]["llm_backend"] == "qwen"
    assert body["meta"]["degraded"] is False
    assert emotion.calls.last.request.headers["X-Model-Server-Token"] == "tok-123"
    assert generate.calls.last.request.headers["X-Model-Server-Token"] == "tok-123"
    sent = generate.calls.last.request.read().decode()
    assert "mình sợ lắm" in sent and "Fear" in sent


def test_no_token_header_when_unset(client, set_env, server):
    set_env(MODEL_SERVER_URL=URL, EMOTION_MODE="remote")
    route = server.post("/emotion").respond(200, json={"label": "Fear", "probs": PROBS})
    chat(client)
    assert "X-Model-Server-Token" not in route.calls.last.request.headers


def test_remote_server_down_degrades(client, remote, server):
    server.post("/emotion").mock(side_effect=httpx.ConnectError("refused"))
    server.post("/generate").mock(side_effect=httpx.ConnectError("refused"))
    r = chat(client)
    assert r.status_code == 200
    body = r.json()
    assert body["emotion"]["label"] == "Other"
    assert body["meta"]["degraded"] is True
    assert any(w.startswith("emotion") for w in body["meta"]["warnings"])
    assert body["meta"]["llm_backend"] == "canned"


def test_remote_timeout_degrades(client, remote, server):
    server.post("/emotion").mock(side_effect=httpx.ReadTimeout("slow"))
    server.post("/generate").respond(200, json={"reply": "ok?"})
    body = chat(client).json()
    assert body["emotion"]["label"] == "Other"
    assert body["meta"]["degraded"] is True
    assert any("emotion" in w and "quá thời gian" in w for w in body["meta"]["warnings"])


def test_remote_http_error_degrades(client, remote, server):
    server.post("/emotion").respond(500, json={"detail": "boom"})
    server.post("/generate").respond(200, json={"reply": "ok?"})
    body = chat(client).json()
    assert body["emotion"]["label"] == "Other"
    assert any(w.startswith("emotion") for w in body["meta"]["warnings"])


@pytest.mark.parametrize(
    "bad",
    [
        {"label": "Joy", "probs": PROBS},
        {"label": "Fear", "probs": {"Fear": 1.0}},
        {"nope": 1},
        "not-a-dict",
    ],
)
def test_remote_bad_schema_degrades(client, remote, server, bad):
    server.post("/emotion").respond(200, json=bad)
    server.post("/generate").respond(200, json={"reply": "ok?"})
    body = chat(client).json()
    assert body["emotion"]["label"] == "Other"
    assert body["meta"]["degraded"] is True


def test_remote_non_json_degrades(client, remote, server):
    server.post("/emotion").respond(200, text="<html>ngrok</html>")
    server.post("/generate").respond(200, json={"reply": "ok?"})
    assert chat(client).json()["meta"]["degraded"] is True


def test_remote_generate_bad_schema_falls_back_to_canned(client, remote, server):
    server.post("/emotion").respond(200, json={"label": "Fear", "probs": PROBS})
    server.post("/generate").respond(200, json={"text": "sai khoá"})
    body = chat(client).json()
    assert body["meta"]["llm_backend"] == "canned"
    assert body["emotion"]["label"] == "Fear"
    assert any(w.startswith("llm") for w in body["meta"]["warnings"])


def test_remote_speech_uses_transcribe_and_prosody(client, remote, server, audio_samples):
    tr = server.post("/transcribe").respond(200, json={"text": "mình rất sợ"})
    pr = server.post("/prosody").respond(
        200, json={"arousal": "high", "pitch_mean": 200.0, "energy_rms": 0.1, "speech_rate": 4.0}
    )
    server.post("/emotion").respond(200, json={"label": "Fear", "probs": PROBS})
    server.post("/generate").respond(200, json={"reply": "ok?"})
    r = client.post(
        "/api/chat",
        data={"session_id": "s1"},
        files={"audio_file": ("a.wav", audio_samples["wav"], "audio/wav")},
    )
    body = r.json()
    assert r.status_code == 200
    assert body["transcript"] == "mình rất sợ"
    assert body["emotion"]["arousal"] == "high"
    assert body["meta"]["modules"]["speech"] == "remote"
    assert b"RIFF" in tr.calls.last.request.read()
    assert pr.called


def test_health_na_without_remote(client, set_env):
    assert client.get("/api/health").json()["model_server"] == "n/a"


def test_health_up_down_and_cache(client, remote, server, monkeypatch):
    route = server.get("/health").respond(200, json={"ok": True, "modules": []})
    assert client.get("/api/health").json() == {"ok": True, "model_server": "up"}
    assert client.get("/api/health").json()["model_server"] == "up"
    assert route.call_count == 1  # lần hai lấy từ cache

    now = {"t": 1_000_000.0}

    class FakeTime:
        @staticmethod
        def monotonic():
            return now["t"]

    monkeypatch.setattr(model_server, "time", FakeTime)
    model_server.reset_state()
    server.get("/health").mock(side_effect=httpx.ConnectError("refused"))
    assert client.get("/api/health").json()["model_server"] == "down"
    server.get("/health").respond(200, json={"ok": True})
    assert client.get("/api/health").json()["model_server"] == "down"  # còn trong cache
    now["t"] += 11
    assert client.get("/api/health").json()["model_server"] == "up"


def test_health_down_when_not_ok(client, remote, server):
    server.get("/health").respond(200, json={"ok": False})
    assert client.get("/api/health").json()["model_server"] == "down"


@pytest.mark.parametrize("env", [{"SAFETY_MODE": "remote"}, {"MUSIC_MODE": "remote"}])
def test_remote_safety_or_music_fails_at_startup(set_env, env):
    set_env(MODEL_SERVER_URL=URL, **env)
    with pytest.raises(ValueError, match="remote"):
        create_app()
    with pytest.raises(ValueError, match="remote"), TestClient(app):
        pass


def test_remote_without_url_fails_at_startup(set_env):
    set_env(EMOTION_MODE="remote")
    with pytest.raises(ValueError, match="MODEL_SERVER_URL"):
        create_app()
    with pytest.raises(ValueError, match="MODEL_SERVER_URL"), TestClient(app):
        pass


def test_remote_reply_keeps_tag_until_backend_strips_it(client, remote, server):
    server.post("/emotion").respond(200, json={"label": "Fear", "probs": PROBS})
    server.post("/generate").respond(200, json={"reply": "[NHAC:CO]\nMình ở đây nghe bạn?"})
    body = chat(client).json()
    assert body["reply"] == "Mình ở đây nghe bạn?"
    assert body["meta"]["music_decision"] == "llm"
    assert body["songs"]
