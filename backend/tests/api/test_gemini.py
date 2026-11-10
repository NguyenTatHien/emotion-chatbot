"""Chuỗi dự phòng LLM: implementation đang chọn -> Gemini -> câu soạn sẵn."""

import json
import logging

import httpx
import pytest
import respx

from app import fallbacks

URL = "http://model.test"
KEY = "AIza-SECRET-KEY-9876"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
GEMINI_OK = {
    "candidates": [{"content": {"parts": [{"text": "Mình nghe bạn đây. Bạn kể thêm nhé?"}]}}]
}


@pytest.fixture
def remote_llm(set_env):
    set_env(MODEL_SERVER_URL=URL, LLM_MODE="remote", GEMINI_API_KEY=KEY, GEMINI_MODEL="gem-test")


@pytest.fixture
def net():
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{URL}/generate").mock(side_effect=httpx.ConnectError("refused"))
        yield mock


def chat(client, message="mình buồn quá"):
    return client.post("/api/chat", data={"session_id": "s1", "message": message}).json()


def test_mock_mode_reports_mock(client):
    body = chat(client)
    assert body["meta"]["llm_backend"] == "mock"
    assert body["meta"]["degraded"] is False


def test_gemini_used_when_qwen_fails(client, remote_llm, net):
    route = net.post(GEMINI_URL.format("gem-test")).respond(200, json=GEMINI_OK)
    chat(client, "câu đầu")
    body = chat(client)
    assert body["reply"] == "Mình nghe bạn đây. Bạn kể thêm nhé?"
    assert body["meta"]["llm_backend"] == "gemini"
    assert body["meta"]["degraded"] is True
    assert any(w.startswith("llm") for w in body["meta"]["warnings"])

    req = route.calls.last.request
    assert req.headers["x-goog-api-key"] == KEY
    assert KEY not in str(req.url)
    payload = json.loads(req.read())
    assert "đồng cảm" in payload["systemInstruction"]["parts"][0]["text"]
    contents = payload["contents"]
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    last = contents[-1]["parts"][0]["text"]
    assert "mình buồn quá" in last and "Cảm xúc" in last


def test_gemini_history_capped_at_six_turns(client, remote_llm, net):
    route = net.post(GEMINI_URL.format("gem-test")).respond(200, json=GEMINI_OK)
    for i in range(8):
        chat(client, f"lượt {i}")
    contents = json.loads(route.calls.last.request.read())["contents"]
    assert len(contents) == 12 + 1


def test_gemini_error_falls_back_to_canned_without_leaking_key(client, remote_llm, net, caplog):
    net.post(GEMINI_URL.format("gem-test")).respond(
        400, json={"error": {"message": f"API key not valid: {KEY}"}}
    )
    with caplog.at_level(logging.DEBUG):
        body = chat(client)
    assert body["meta"]["llm_backend"] == "canned"
    assert body["meta"]["degraded"] is True
    assert body["reply"] in fallbacks.CANNED_REPLIES.values()
    assert any(w.startswith("gemini") for w in body["meta"]["warnings"])
    assert KEY not in json.dumps(body, ensure_ascii=False)
    assert KEY not in caplog.text


def test_gemini_timeout_and_empty_response_fall_back(client, remote_llm, net):
    route = net.post(GEMINI_URL.format("gem-test"))
    route.mock(side_effect=httpx.ReadTimeout("slow"))
    assert chat(client)["meta"]["llm_backend"] == "canned"
    route.mock(return_value=httpx.Response(200, json={"candidates": []}))
    assert chat(client)["meta"]["llm_backend"] == "canned"


def test_no_gemini_key_goes_straight_to_canned(client, set_env, net):
    set_env(MODEL_SERVER_URL=URL, LLM_MODE="remote")
    gemini = net.post(GEMINI_URL.format("gemini-3.5-flash-lite")).respond(200, json=GEMINI_OK)
    body = chat(client)
    assert body["meta"]["llm_backend"] == "canned"
    assert body["meta"]["degraded"] is True
    assert not gemini.called


def test_safety_turn_never_calls_llm(client, remote_llm, net):
    gemini = net.post(GEMINI_URL.format("gem-test")).respond(200, json=GEMINI_OK)
    body = chat(client, "mình muốn chết")
    assert body["safety"] is True
    assert not gemini.called


# --- LLM_MODE=gemini: Gemini là nguồn chính, không coi là dự phòng ---


@pytest.fixture
def gemini_mode(set_env):
    set_env(LLM_MODE="gemini", GEMINI_API_KEY=KEY, GEMINI_MODEL="gem-test")


def test_gemini_mode_is_primary_not_degraded(client, gemini_mode):
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post(GEMINI_URL.format("gem-test")).respond(200, json=GEMINI_OK)
        body = chat(client)
    assert body["reply"] == "Mình nghe bạn đây. Bạn kể thêm nhé?"
    assert body["meta"]["llm_backend"] == "gemini"
    assert body["meta"]["degraded"] is False
    assert body["meta"]["warnings"] == []
    assert body["meta"]["modules"]["llm"] == "gemini"
    assert route.call_count == 1


def test_gemini_mode_failure_goes_to_canned_without_second_call(client, gemini_mode):
    with respx.mock() as mock:
        route = mock.post(GEMINI_URL.format("gem-test")).respond(429, json={})
        body = chat(client)
    assert route.call_count == 1
    assert body["meta"]["llm_backend"] == "canned"
    assert body["meta"]["degraded"] is True
    assert body["reply"] in fallbacks.CANNED_REPLIES.values()


def test_meta_reports_gemini(client, gemini_mode):
    body = client.get("/api/meta").json()
    assert body["llm_backend"] == "gemini"
    assert body["modules"]["llm"] == "gemini"
    assert client.get("/api/health").json()["model_server"] == "n/a"


def test_gemini_mode_requires_key(set_env):
    from app.config import get_settings

    set_env(LLM_MODE="gemini", GEMINI_API_KEY="")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_settings().validate_remote()


@pytest.mark.parametrize("field", ["MODEL_MODE", "EMOTION_MODE", "MUSIC_MODE"])
def test_gemini_only_valid_for_llm(set_env, field):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="không hợp lệ"):
        set_env(**{field: "gemini"})
