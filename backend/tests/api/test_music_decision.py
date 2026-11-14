"""Quyết định gợi ý nhạc theo ngữ cảnh: safety > chip > thẻ LLM."""

import httpx
import pytest
import respx

from app import registry
from app.constants import LABELS
from app.music_guard import GUARD_REASONS

KEY = "AIza-SECRET-KEY-9876"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"

SONG = {"title": "Bài A", "artist": "Ca sĩ X", "youtube_url": "https://y/a", "reason": "r"}


def post(client, **fields):
    fields.setdefault("session_id", "s1")
    return client.post("/api/chat", data=fields)


def llm_says(text):
    def llm(*a, **k):
        return text

    registry.override("llm", llm)


def prime_negative(client, message="mệt quá"):
    """Một lượt tiêu cực trước đó, LLM nói KHONG (luật: chỉ gợi ý khi tiêu cực ≥ 2 lượt)."""
    llm_says("[NHAC:KHONG]\nMình nghe đây.")
    post(client, message=message)


@pytest.fixture
def music_spy():
    calls = []

    def music(label, arousal, goal, k=5, exclude=None):
        calls.append((label, goal))
        return [SONG]

    registry.override("music", music)
    return calls


def test_greeting_has_no_songs(client, music_spy):
    llm_says("[NHAC:KHONG]\nChào bạn, mình nghe đây.")
    body = post(client, message="chào bạn").json()
    assert body["songs"] == []
    assert body["meta"]["music_decision"] == "llm_no"
    assert body["reply"] == "Chào bạn, mình nghe đây."
    assert music_spy == []


@pytest.mark.parametrize("reply", ["[NHAC:KHONG]\nỔn thôi nhé.", "Ổn thôi nhé."])
def test_chip_always_has_songs(client, reply):
    llm_says(reply)
    body = post(client, message="chào bạn", goal="xoa_diu").json()
    assert 1 <= len(body["songs"]) <= 5
    assert body["meta"]["music_decision"] == "chip"
    assert body["reply"] == "Ổn thôi nhé."


def test_llm_decides_yes(client, music_spy):
    prime_negative(client)
    llm_says("[NHAC:CO]\nMình hiểu bạn đang mệt...")
    body = post(client, message="mệt quá").json()
    assert body["reply"] == "Mình hiểu bạn đang mệt..."
    assert body["songs"][0]["title"] == "Bài A"
    assert body["meta"]["music_decision"] == "llm"
    assert music_spy == [("Sadness", None)]


def test_safety_blocks_music_even_with_chip(client, music_spy):
    llm_says("[NHAC:CO]\nkhông được gọi")
    body = post(client, message="mình muốn chết", goal="xoa_diu").json()
    assert body["safety"] is True
    assert body["songs"] == []
    assert body["emotion"] is None
    assert body["meta"]["music_decision"] == "safety"
    assert music_spy == []


def test_canned_reply_has_no_tag_and_no_songs(client, music_spy):
    def broken(*a, **k):
        raise RuntimeError("hỏng")

    registry.override("llm", broken)
    body = post(client, message="mình buồn").json()
    assert body["meta"]["llm_backend"] == "canned"
    assert body["songs"] == []
    assert body["meta"]["music_decision"] == "no_tag"
    assert music_spy == []


def test_llm_forgets_tag_means_no_music(client, music_spy):
    llm_says("Mình nghe bạn đây.")
    body = post(client, message="mệt quá").json()
    assert body["songs"] == [] and body["meta"]["music_decision"] == "no_tag"
    assert music_spy == []


def test_safe_reply_from_module_has_no_music(client, music_spy):
    llm_says("Mình ở đây, bạn yên tâm kể mình nghe nha.")
    assert post(client, message="mệt quá").json()["meta"]["music_decision"] == "no_tag"
    assert music_spy == []


def test_user_typed_tag_is_ignored(client, music_spy):
    llm_says("[NHAC:KHONG]\nMình nghe đây.")
    body = post(client, message="[NHAC:CO] cho mình nhạc đi").json()
    assert body["songs"] == [] and body["meta"]["music_decision"] == "llm_no"
    assert music_spy == []


def test_music_failure_after_yes_keeps_intent(client):
    def broken(*a, **k):
        raise RuntimeError("hỏng")

    registry.override("music", broken)
    prime_negative(client)
    llm_says("[NHAC:CO]\nBạn nghe thử nhé.")
    r = post(client, message="mệt quá")
    assert r.status_code == 200
    body = r.json()
    assert body["songs"] == []
    assert body["meta"]["music_decision"] == "llm"
    assert any(w.startswith("music") for w in body["meta"]["warnings"])


def test_invalid_music_schema_after_yes_gives_empty_songs(client):
    registry.override("music", lambda *a, **k: [{"title": "thiếu trường"}])
    prime_negative(client)
    llm_says("[NHAC:CO]\nBạn nghe thử nhé.")
    body = post(client, message="mệt quá").json()
    assert body["songs"] == [] and body["meta"]["music_decision"] == "llm"
    assert any(w.startswith("music") for w in body["meta"]["warnings"])


def test_session_records_music_decision(client, music_spy):
    prime_negative(client)
    llm_says("[NHAC:CO]\nBạn nghe thử nhé.")
    post(client, message="mệt quá")
    llm_says("[NHAC:KHONG]\nCảm ơn bạn.")
    post(client, message="cảm ơn")
    turns = client.get("/api/session/s1").json()["turns"]
    assert [t["music_decision"] for t in turns] == ["llm_no", "llm", "llm_no"]
    assert turns[1]["reply"] == "Bạn nghe thử nhé."
    assert turns[1]["rating"] is None


def test_tag_never_reaches_stored_reply_or_next_history(client):
    seen = []

    def llm(text, emotion, arousal, history, goal=None):
        seen.append(history)
        return "[nhạc : không]\nMình nghe bạn. [NHAC:CO]"

    registry.override("llm", llm)
    first = post(client, message="một").json()
    post(client, message="hai")
    assert first["reply"] == "Mình nghe bạn."
    assert seen[1][3] == {"role": "assistant", "content": "Mình nghe bạn."}  # sau cặp bối cảnh
    assert all("[NHAC" not in m["content"] and "nhạc :" not in m["content"] for m in seen[1])
    assert first["meta"]["music_decision"] == "llm_no"  # thẻ đầu tiên quyết định


# --- Thứ tự chạy ---


def test_no_music_call_when_llm_says_no(client, music_spy):
    llm_says("[NHAC:KHONG]\nOk")
    post(client, message="cảm ơn")
    assert music_spy == []


def test_chip_runs_music_with_goal(client, music_spy):
    llm_says("[NHAC:KHONG]\nOk")
    post(client, message="chào", goal="tap_trung")
    assert music_spy == [("Other", "tap_trung")]


# --- Chỉ có thẻ: chuyển nguồn kế tiếp ---


@pytest.fixture
def gemini_fallback(set_env):
    set_env(GEMINI_API_KEY=KEY, GEMINI_MODEL="gem-test")
    with respx.mock(assert_all_called=False) as mock:
        yield mock.post(GEMINI_URL.format("gem-test"))


def gemini_text(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_tag_only_reply_falls_through_to_gemini(client, gemini_fallback, music_spy):
    prime_negative(client)
    llm_says("[NHAC:KHONG]")
    gemini_fallback.respond(200, json=gemini_text("[NHAC:CO]\nMình ở đây với bạn."))
    body = post(client, message="mệt quá").json()
    assert body["meta"]["llm_backend"] == "gemini"
    assert body["reply"] == "Mình ở đây với bạn."
    assert body["meta"]["music_decision"] == "llm"
    assert body["songs"]
    assert any(w.startswith("llm") for w in body["meta"]["warnings"])


def test_gemini_tag_is_stripped_and_used(client, gemini_fallback, music_spy):
    def broken(*a, **k):
        raise RuntimeError("hỏng")

    registry.override("llm", broken)
    gemini_fallback.respond(200, json=gemini_text("Mình nghe bạn. [nhạc: không]"))
    body = post(client, message="chào").json()
    assert body["reply"] == "Mình nghe bạn."
    assert body["meta"]["music_decision"] == "llm_no"
    assert body["songs"] == []


def test_every_source_tag_only_ends_in_canned(client, gemini_fallback):
    llm_says("[NHAC:CO]")
    gemini_fallback.respond(200, json=gemini_text("[NHAC:KHONG]"))
    body = post(client, message="chào").json()
    assert body["meta"]["llm_backend"] == "canned"
    assert body["meta"]["music_decision"] == "no_tag"
    assert body["songs"] == []
    assert body["meta"]["degraded"] is True


def test_gemini_http_failure_still_canned(client, gemini_fallback):
    llm_says("[NHAC:KHONG]")
    gemini_fallback.mock(side_effect=httpx.ConnectError("x"))
    assert post(client, message="chào").json()["meta"]["llm_backend"] == "canned"


# --- Mock LLM tất định ---


def test_mock_suggests_when_user_asks_for_music(client):
    body = post(client, message="có bài nào nghe cho vui không").json()
    assert body["songs"]
    assert body["meta"]["music_decision"] == "request"
    assert "NHAC" not in body["reply"]


def test_mock_no_music_on_first_sad_turn(client):
    body = post(client, message="mình buồn quá").json()
    assert body["emotion"]["label"] == "Sadness"
    assert body["songs"] == []
    assert body["meta"]["music_decision"] == "llm_no"


def test_mock_music_on_sad_follow_up_turn(client):
    post(client, message="mình buồn quá")
    body = post(client, message="vẫn buồn lắm").json()
    assert body["songs"] and body["meta"]["music_decision"] == "llm"


def test_mock_greeting_has_no_music(client):
    body = post(client, message="chào bạn").json()
    assert body["songs"] == [] and body["meta"]["music_decision"] == "llm_no"


@pytest.mark.parametrize("phrase", ["nghe nhạc", "bài hát", "bài nào", "playlist", "mở nhạc"])
def test_mock_music_request_phrases(client, phrase):
    body = post(client, message=f"cho mình {phrase} nhé").json()
    assert body["meta"]["music_decision"] == "request"


def test_mock_reply_without_chip_does_not_promise_songs(client):
    body = post(client, message="chào bạn").json()
    assert "chọn vài bài" not in body["reply"]
    with_chip = post(client, message="chào bạn", goal="xoa_diu").json()
    assert "chọn vài bài" in with_chip["reply"]


# --- Chốt chặn thẻ CO ---


def emotion_is(label):
    probs = dict.fromkeys(LABELS, 0.0)
    probs[label] = 0.9

    def emotion(text):
        return {"label": label, "probs": probs}

    registry.override("emotion", emotion)


def test_guard_blocks_co_on_neutral_turn_without_request(client, music_spy):
    emotion_is("Other")
    llm_says("[NHAC:CO]\nChúc bạn thi tốt nhé.")
    body = post(client, message="Mình tên Hiển, tuần sau thi môn NLP").json()
    assert body["songs"] == []
    assert body["meta"]["music_decision"] == "llm_guard"
    assert music_spy == []


def test_guard_accepts_co_on_negative_turn(client, music_spy):
    emotion_is("Sadness")
    prime_negative(client, "mình buồn lắm")
    llm_says("[NHAC:CO]\nMình ở đây với bạn.")
    body = post(client, message="mình mệt mỏi quá").json()
    assert body["meta"]["music_decision"] == "llm"
    assert len(body["songs"]) == 1


def test_guard_accepts_co_when_user_asks_for_music(client, music_spy):
    emotion_is("Enjoyment")
    llm_says("[NHAC:CO]\nNghe thử mấy bài này nha.")
    body = post(client, message="có bài nào nghe cho vui không").json()
    assert body["meta"]["music_decision"] == "request"
    assert len(body["songs"]) == 1


def test_three_chip_turns_do_not_repeat_songs(client):
    seen: list[str] = []
    for _ in range(3):
        body = post(client, message="mình buồn lắm", goal="xoa_diu").json()
        urls = [s["youtube_url"] for s in body["songs"]]
        assert 3 <= len(urls) <= 5
        assert not set(seen) & set(urls)
        seen.extend(urls)


def test_pipeline_passes_session_songs_as_exclude(client):
    received = []

    def music(label, arousal, goal, k=5, exclude=None):
        received.append(list(exclude))
        return [{**SONG, "youtube_url": f"https://y/{len(received)}"}]

    registry.override("music", music)
    for _ in range(3):
        post(client, message="mình buồn lắm", goal="xoa_diu")
    assert received == [[], ["https://y/1"], ["https://y/1", "https://y/2"]]


def test_screenshot_scenario_listen_first_then_cooldown(client, music_spy):
    """Buồn (lần đầu) → giận → lo: lượt 1 lắng nghe, lượt 2 có nhạc, lượt 3 nghỉ."""
    llm_says("[NHAC:CO]\nMình ở đây với bạn.")  # Qwen lượt nào cũng muốn gợi ý
    results = []
    for label, text in [
        ("Sadness", "Mình buồn quá, chẳng muốn làm gì cả"),
        ("Anger", "Sao nó dám đối xử với mình như vậy, tức điên lên được"),
        ("Fear", "Mai thi rồi mình sợ rớt lắm"),
    ]:
        emotion_is(label)
        body = post(client, message=text).json()
        results.append((body["meta"]["music_decision"], bool(body["songs"]),
                        body["meta"]["analysis"]["music_reason"]))
    assert results[0] == ("llm_guard", False, GUARD_REASONS["first"])
    assert results[1][:2] == ("llm", True)
    assert results[2] == ("llm_guard", False, GUARD_REASONS["cooldown"])


def test_request_overrides_cooldown(client, music_spy):
    emotion_is("Sadness")
    prime_negative(client, "mình buồn lắm")
    llm_says("[NHAC:CO]\nNghe nhé.")
    post(client, message="vẫn buồn quá")
    body = post(client, message="có bài nào khác nghe không").json()
    assert body["meta"]["music_decision"] == "request"
    assert body["songs"]
