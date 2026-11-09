import csv
import io
import json
from pathlib import Path

from app.config import get_settings


def chat(client, message="hôm nay mình mệt quá", session="s1", **extra):
    r = client.post("/api/chat", data={"session_id": session, "message": message, **extra})
    return r.json()


def lines():
    path = Path(get_settings().FEEDBACK_PATH)
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def post(client, turn_id, rating="up", session="s1"):
    return client.post(
        "/api/feedback", json={"session_id": session, "turn_id": turn_id, "rating": rating}
    )


def export(client, token="adm-1"):
    return client.get("/api/feedback/export", headers={"Authorization": f"Bearer {token}"})


def test_feedback_stored_without_text(client):
    body = chat(client, "bí mật riêng tư của mình", goal="xoa_diu")
    r = post(client, body["turn_id"])
    assert r.status_code == 200
    rows = lines()
    assert len(rows) == 1
    row = rows[0]
    assert row["rating"] == "up" and row["turn_id"] == body["turn_id"]
    assert row["emotion_label"] == body["emotion"]["label"]
    assert row["goal"] == "xoa_diu"
    assert row["llm_backend"] == "mock" and row["safety"] is False
    assert set(row) == {
        "session_id", "turn_id", "rating", "emotion_label", "arousal", "goal", "safety",
        "llm_backend", "created_at",
    }  # fmt: skip
    raw = Path(get_settings().FEEDBACK_PATH).read_text(encoding="utf-8")
    assert "bí mật riêng tư" not in raw
    assert body["reply"] not in raw


def test_feedback_unknown_turn_404(client):
    chat(client)
    assert post(client, "khong-co").status_code == 404
    assert post(client, "x", session="khac").status_code == 404


def test_feedback_validation(client):
    body = chat(client)
    r = client.post(
        "/api/feedback",
        json={"session_id": "s1", "turn_id": body["turn_id"], "rating": "meh"},
    )
    assert r.status_code == 422


def test_feedback_overwrite_and_export(client, set_env):
    set_env(ADMIN_TOKEN="adm-1")
    t1 = chat(client, "tin nhắn thứ nhất")["turn_id"]
    t2 = chat(client, "tin nhắn thứ hai")["turn_id"]
    post(client, t1, "up")
    post(client, t2, "down")
    post(client, t1, "down")
    r = export(client)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert {x["turn_id"]: x["rating"] for x in rows} == {t1: "down", t2: "down"}
    assert len(rows) == 2
    assert "tin nhắn" not in r.text


def test_export_auth(client, set_env):
    assert client.get("/api/feedback/export").status_code == 404  # ADMIN_TOKEN rỗng
    assert export(client, "x").status_code == 404
    set_env(ADMIN_TOKEN="adm-1")
    assert client.get("/api/feedback/export").status_code == 401
    assert export(client, "sai").status_code == 401
    basic = client.get("/api/feedback/export", headers={"Authorization": "Basic adm-1"})
    assert basic.status_code == 401


def test_export_empty_has_header_only(client, set_env):
    set_env(ADMIN_TOKEN="adm-1")
    r = export(client)
    assert r.text.strip().split(",")[0] == "session_id"
    assert len(r.text.strip().splitlines()) == 1


def test_export_neutralises_csv_formulas(client, set_env):
    set_env(ADMIN_TOKEN="adm-1")
    body = chat(client, session="=cmd")
    post(client, body["turn_id"], session="=cmd")
    rows = list(csv.DictReader(io.StringIO(export(client).text)))
    assert rows[0]["session_id"] == "'=cmd"


def test_safety_turn_feedback_records_flag(client):
    body = chat(client, "mình muốn chết")
    post(client, body["turn_id"], "down")
    row = lines()[0]
    assert row["safety"] is True and row["emotion_label"] is None
