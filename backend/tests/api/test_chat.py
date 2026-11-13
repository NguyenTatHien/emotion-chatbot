import time

from app import registry

LABELS = {"Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise"}


def post(client, **fields):
    return client.post("/api/chat", data=fields)


def test_full_mock_turn(client):
    r = post(client, session_id="s1", message="hôm nay mệt quá", goal="xoa_diu")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"turn_id", "reply", "transcript", "emotion", "songs", "safety", "meta"}
    assert body["safety"] is False
    assert body["transcript"] is None
    assert body["emotion"]["label"] == "Sadness"
    assert set(body["emotion"]["probs"]) == LABELS
    assert abs(sum(body["emotion"]["probs"].values()) - 1) < 1e-6
    assert 3 <= len(body["songs"]) <= 5
    assert set(body["songs"][0]) == {"title", "artist", "youtube_url", "reason"}
    meta = body["meta"]
    assert meta["degraded"] is False and meta["warnings"] == []
    assert meta["music_decision"] == "chip"
    assert meta["modules"] == {k: "mock" for k in ("emotion", "speech", "safety", "llm", "music")}
    assert meta["model_mode"] == "mock"
    assert isinstance(meta["latency_ms"], int) and meta["latency_ms"] >= 0


def test_missing_all_inputs_returns_400(client):
    r = post(client, session_id="s1")
    assert r.status_code == 400
    assert "message" in r.json()["detail"]


def test_blank_inputs_return_400(client):
    assert post(client, session_id="s1", message="   ", transcript_hint="").status_code == 400


def test_missing_session_id_returns_400(client):
    assert post(client, message="xin chào").status_code == 400


def test_invalid_goal_returns_400(client):
    assert post(client, session_id="s1", message="hi", goal="ngu_ngon").status_code == 400


def test_valid_goal_accepted(client):
    assert post(client, session_id="s1", message="hi", goal="tap_trung").status_code == 200


def test_message_too_long_returns_400(client):
    assert post(client, session_id="s1", message="a" * 1001).status_code == 400
    assert post(client, session_id="s1", message="a" * 1000).status_code == 200


def test_audio_only_uses_speech_module(client, audio_samples):
    r = client.post(
        "/api/chat",
        data={"session_id": "s1"},
        files={"audio_file": ("voice.webm", audio_samples["webm"], "audio/webm")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"] == "hôm nay mình thấy hơi mệt"
    assert body["emotion"]["arousal"] == "medium"
    assert body["emotion"]["label"] == "Sadness"


def test_audio_too_large_returns_413(client, set_env):
    set_env(MAX_AUDIO_MB=1)
    r = client.post(
        "/api/chat",
        data={"session_id": "s1"},
        files={"audio_file": ("a.wav", b"0" * (1024 * 1024 + 10), "audio/wav")},
    )
    assert r.status_code == 413


def test_message_has_priority_over_transcript_hint(client):
    seen = []

    def spy(text):
        seen.append(text)
        return {"label": "Other", "probs": {k: 1 / 7 for k in LABELS}}

    registry.override("emotion", spy)
    post(client, session_id="s1", message="A", transcript_hint="B")
    assert seen == ["A"]


def test_transcript_hint_used_when_no_message(client):
    r = post(client, session_id="s1", transcript_hint="mình buồn")
    assert r.status_code == 200
    assert r.json()["emotion"]["label"] == "Sadness"


def test_safety_path_skips_other_modules(client):
    calls = []

    def boom(name):
        def fn(*a, **k):
            calls.append(name)
            raise AssertionError(name)

        return fn

    for name in ("emotion", "llm", "music"):
        registry.override(name, boom(name))
    r = post(client, session_id="s1", message="mình muốn chết")
    assert r.status_code == 200
    body = r.json()
    assert body["safety"] is True
    assert body["emotion"] is None
    assert body["songs"] == []
    assert body["reply"].strip()
    assert body["meta"]["degraded"] is False
    assert calls == []


def test_emotion_error_degrades(client):
    def broken(text):
        raise RuntimeError("hỏng")

    registry.override("emotion", broken)
    r = post(client, session_id="s1", message="hôm nay thế nào")
    assert r.status_code == 200
    body = r.json()
    assert body["emotion"]["label"] == "Other"
    assert abs(sum(body["emotion"]["probs"].values()) - 1) < 1e-6
    assert body["meta"]["degraded"] is True
    assert any("emotion" in w for w in body["meta"]["warnings"])


def test_safety_error_falls_back_to_keywords(client):
    def broken(text):
        raise RuntimeError("hỏng")

    registry.override("safety", broken)
    body = post(client, session_id="s1", message="mình muốn tự tử").json()
    assert body["safety"] is True
    assert body["meta"]["degraded"] is True
    assert any("safety" in w for w in body["meta"]["warnings"])

    body = post(client, session_id="s2", message="mình đang vui").json()
    assert body["safety"] is False
    assert body["meta"]["degraded"] is True


def test_safety_error_unaccented_keyword(client):
    registry.override("safety", lambda text: (_ for _ in ()).throw(RuntimeError("x")))
    assert post(client, session_id="s1", message="toi muon tu tu").json()["safety"] is True


def test_llm_timeout_uses_canned_reply(client, set_env):
    set_env(LLM_TIMEOUT="0.1")

    def slow(*a, **k):
        time.sleep(0.6)
        return "quá muộn"

    registry.override("llm", slow)
    body = post(client, session_id="s1", message="mình buồn quá").json()
    assert body["reply"] != "quá muộn"
    assert body["reply"].endswith("?")
    assert body["meta"]["degraded"] is True
    assert any("llm" in w for w in body["meta"]["warnings"])


def test_music_error_returns_empty_songs(client):
    def broken(*a, **k):
        raise RuntimeError("hỏng")

    registry.override("music", broken)
    body = post(client, session_id="s1", message="mình buồn", goal="xoa_diu").json()
    assert body["songs"] == []
    assert body["meta"]["degraded"] is True
    assert any("music" in w for w in body["meta"]["warnings"])


def test_local_stub_module_degrades_not_500(client, set_env):
    set_env(MUSIC_MODE="local")
    r = post(client, session_id="s1", message="mình buồn", goal="xoa_diu")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["modules"]["music"] == "local"
    assert body["meta"]["degraded"] is True


def test_remote_mode_degrades_not_500(client, set_env):
    set_env(EMOTION_MODE="remote")
    r = post(client, session_id="s1", message="mình buồn")
    assert r.status_code == 200
    assert r.json()["meta"]["degraded"] is True
    assert r.json()["meta"]["modules"]["emotion"] == "remote"
