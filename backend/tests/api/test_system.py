from app import registry


def test_health_without_remote(client):
    assert client.get("/api/health").json() == {"ok": True, "model_server": "n/a"}


def test_meta_lists_configuration(client):
    body = client.get("/api/meta").json()
    assert len(body["labels"]) == 7
    assert body["goals"] == ["xoa_diu", "nang_mood", "tap_trung", "giai_toa"]
    assert set(body["modules"]) == {"emotion", "speech", "safety", "llm", "music"}
    assert body["model_mode"] == "mock"
    assert "llm_backend" in body


def test_session_keeps_order(client):
    ids = []
    for text in ("một", "hai"):
        r = client.post("/api/chat", data={"session_id": "s1", "message": text})
        ids.append(r.json()["turn_id"])
    body = client.get("/api/session/s1").json()
    assert body["session_id"] == "s1"
    assert [t["turn_id"] for t in body["turns"]] == ids
    assert [t["user_text"] for t in body["turns"]] == ["một", "hai"]
    turn = body["turns"][0]
    assert set(turn) == {
        "turn_id", "user_text", "transcript", "reply", "emotion", "songs", "safety", "goal",
        "llm_backend", "music_decision", "rating", "created_at",
    }


def test_session_unknown_is_empty(client):
    r = client.get("/api/session/khong-co")
    assert r.status_code == 200
    assert r.json() == {"session_id": "khong-co", "turns": []}


def test_session_stores_safety_turns(client):
    client.post("/api/chat", data={"session_id": "s1", "message": "mình muốn chết"})
    turns = client.get("/api/session/s1").json()["turns"]
    assert len(turns) == 1 and turns[0]["safety"] is True


def test_cors_allows_dev_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_blocks_unknown_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_delete_session_with_data(client):
    seen = {}

    def spy(text, emotion, arousal, history, goal=None):
        seen["history"] = history
        return "ok?"

    for text in ("một", "hai", "ba"):
        client.post("/api/chat", data={"session_id": "s1", "message": text})
    r = client.delete("/api/session/s1")
    assert r.status_code == 204
    assert r.content == b""
    assert client.get("/api/session/s1").json()["turns"] == []

    registry.override("llm", spy)
    client.post("/api/chat", data={"session_id": "s1", "message": "lại từ đầu"})
    # Phiên đã xoá: không còn lượt cũ, chỉ có ghi chú bối cảnh của lượt thứ 1.
    assert len(seen["history"]) == 2
    assert "lượt thứ 1" in seen["history"][0]["content"]
    assert "một" not in str(seen["history"])


def test_delete_session_only_affects_that_session(client):
    client.post("/api/chat", data={"session_id": "a", "message": "của a"})
    client.post("/api/chat", data={"session_id": "b", "message": "của b"})
    assert client.delete("/api/session/a").status_code == 204
    assert client.get("/api/session/a").json()["turns"] == []
    assert len(client.get("/api/session/b").json()["turns"]) == 1


def test_delete_unknown_session_is_204(client):
    assert client.delete("/api/session/khong-co").status_code == 204


def test_delete_session_twice_is_idempotent(client):
    client.post("/api/chat", data={"session_id": "s1", "message": "một"})
    assert client.delete("/api/session/s1").status_code == 204
    assert client.delete("/api/session/s1").status_code == 204


def test_delete_session_id_length_limit(client):
    assert client.delete(f"/api/session/{'x' * 64}").status_code == 204
    assert client.delete(f"/api/session/{'x' * 65}").status_code == 422
