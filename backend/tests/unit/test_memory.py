"""Bộ nhớ hội thoại: dựng history cho LLM, hồ sơ nhạc và tóm tắt nền."""

import asyncio
import json

import httpx
import pytest
import respx

from app import gemini, memory, registry
from app.pipeline import handle_chat
from app.schemas import SessionTurn, Song
from app.session import SessionStore, store

KEY = "AIza-SECRET-KEY-9876"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def song(title="A", artist="X"):
    return Song(title=title, artist=artist, youtube_url="https://y", reason="r")


def turn(i, songs=None, **kw):
    return SessionTurn(
        turn_id=f"t{i}",
        user_text=f"hỏi {i}",
        reply=f"đáp {i}",
        songs=songs or [],
        created_at="t",
        **kw,
    )


async def fill(session_id, n, songs_at=()):
    for i in range(1, n + 1):
        await store.append_turn(session_id, turn(i, [song()] if i in songs_at else None))


@pytest.fixture(autouse=True)
async def _drain_after():
    yield
    await memory.drain()


@pytest.fixture
def gemini_key(set_env):
    return set_env(GEMINI_API_KEY=KEY, GEMINI_MODEL="gem-test")


def silent_llm(text, emotion, arousal, history, goal=None):
    return "ok?"


async def run_turns(count, start=1, session="s"):
    registry.override("llm", silent_llm)
    for i in range(start, start + count):
        await handle_chat(session, message=f"lượt {i}")


# --- Lịch sử gửi LLM ---


async def test_sessions_are_isolated():
    await fill("a", 3)
    assert await memory.build_history("b") == []


async def test_short_session_has_no_context_pair():
    await fill("s", 3)
    history = await memory.build_history("s")
    assert len(history) == 6
    assert [m["role"] for m in history] == ["user", "assistant"] * 3
    assert history[0] == {"role": "user", "content": "hỏi 1"}
    assert not any(m["content"].startswith(memory.CONTEXT_MARKER) for m in history)


async def test_songs_without_summary_give_context_pair():
    await store.append_turn("s", turn(1, [song("A", "X"), song("B", "Y")]))
    await store.append_turn("s", turn(2))
    history = await memory.build_history("s")
    assert len(history) == 2 + 4
    assert history[0]["role"] == "user"
    assert history[0]["content"].startswith(memory.CONTEXT_MARKER)
    assert "A – X" in history[0]["content"] and "B – Y" in history[0]["content"]
    assert "lượt 1" in history[0]["content"]
    assert "Tóm tắt" not in history[0]["content"]
    assert history[1] == {"role": "assistant", "content": memory.CONTEXT_ACK}
    assert history[2]["content"] == "hỏi 1"


async def test_long_session_with_summary_uses_context_and_unsummarized_turns():
    await fill("s", 12, songs_at=(2,))
    state = store._sessions["s"]
    state.summary = "Người dùng kể chuyện thi cử."
    state.summarized_count = 4
    history = await memory.build_history("s")
    assert len(history) == 2 + 16
    assert "Người dùng kể chuyện thi cử." in history[0]["content"]
    # hồ sơ nhạc lấy cả từ lượt đã tóm tắt (lượt 2)
    assert "lượt 2: A – X" in history[0]["content"]
    assert history[2]["content"] == "hỏi 5"
    assert history[-1]["content"] == "đáp 12"


async def test_verbatim_turns_capped_when_summary_is_late(set_env):
    set_env(HISTORY_TURNS=6, SUMMARY_BATCH_TURNS=4)
    await fill("s", 30)
    history = await memory.build_history("s")
    assert len(history) == 2 * (6 + 2 * 4)
    assert history[-1]["content"] == "đáp 30"
    assert history[0]["content"] == "hỏi 17"


async def test_music_profile_has_rating_and_limit_of_five_turns():
    await fill("s", 8, songs_at=range(1, 9))
    await store.set_rating("s", "t4", "down")
    await store.set_rating("s", "t8", "up")
    context = (await memory.build_history("s"))[0]["content"]
    assert "lượt 3:" not in context
    assert "lượt 4: A – X (người dùng: không thích)" in context
    assert "lượt 8: A – X (người dùng: thích)" in context
    assert context.count("A – X") == 5


async def test_rating_via_feedback_shows_in_next_context(client):
    registry.override(
        "music",
        lambda *a, **k: [
            {"title": "A", "artist": "X", "youtube_url": "https://y", "reason": "r"}
        ],
    )
    r = client.post(
        "/api/chat", data={"session_id": "s1", "message": "mình mệt", "goal": "xoa_diu"}
    )
    turn_id = r.json()["turn_id"]
    seen = {}

    def spy(text, emotion, arousal, history, goal=None):
        seen["history"] = history
        return "ok?"

    registry.override("llm", spy)
    resp = client.post(
        "/api/feedback", json={"session_id": "s1", "turn_id": turn_id, "rating": "down"}
    )
    assert resp.status_code == 200
    client.post("/api/chat", data={"session_id": "s1", "message": "tiếp"})
    assert "A – X (người dùng: không thích)" in seen["history"][0]["content"]


async def test_history_uses_stripped_reply():
    def llm(text, emotion, arousal, history, goal=None):
        return "[NHAC:CO]\nMình nghe đây."

    registry.override("llm", llm)
    await handle_chat("s", message="chào")
    history = await memory.build_history("s")
    assert history[-1] == {"role": "assistant", "content": "Mình nghe đây."}
    assert not any("NHAC" in m["content"] for m in history)


async def test_history_turns_setting_changes_cap(set_env):
    set_env(HISTORY_TURNS=2, SUMMARY_BATCH_TURNS=1)
    await fill("s", 10)
    assert len(await memory.build_history("s")) == 2 * (2 + 2)


async def test_evicted_session_loses_memory():
    small = SessionStore(max_turns=5, max_sessions=1)
    await small.append_turn("a", turn(1))
    await small.begin_summary("a")
    await small.append_turn("b", turn(1))
    snap = await small.snapshot("a")
    assert snap.total == 0 and snap.summary == ""


async def test_absolute_numbering_survives_deque_overflow():
    small = SessionStore(max_turns=3, max_sessions=5)
    for i in range(1, 6):
        await small.append_turn("a", turn(i, [song()] if i == 5 else None))
    snap = await small.snapshot("a")
    assert snap.total == 5 and snap.first_index == 2
    assert "lượt 5: A – X" in memory._music_profile(snap)


# --- Tóm tắt nền ---


async def test_summary_runs_at_threshold(gemini_key, monkeypatch):
    calls = []

    async def fake(previous, turns):
        calls.append((previous, [t.user_text for t in turns]))
        return "Tóm tắt mới."

    monkeypatch.setattr(gemini, "summarize", fake)
    await run_turns(9)
    await memory.drain()
    assert calls == []
    await run_turns(1, start=10)
    await memory.drain()
    assert calls == [("", ["lượt 1", "lượt 2", "lượt 3", "lượt 4"])]
    snap = await store.snapshot("s")
    assert snap.summary == "Tóm tắt mới." and snap.summarized_count == 4
    history = await memory.build_history("s")
    assert "Tóm tắt mới." in history[0]["content"]
    assert history[2]["content"] == "lượt 5"


async def test_second_batch_merges_previous_summary(gemini_key, monkeypatch):
    calls = []

    async def fake(previous, turns):
        calls.append(previous)
        return f"S{len(calls)}"

    monkeypatch.setattr(gemini, "summarize", fake)
    await run_turns(10)
    await memory.drain()
    await run_turns(4, start=11)
    await memory.drain()
    assert calls == ["", "S1"]
    snap = await store.snapshot("s")
    assert snap.summary == "S2" and snap.summarized_count == 8


async def test_response_does_not_wait_for_summary(gemini_key, monkeypatch):
    release = asyncio.Event()

    async def slow(previous, turns):
        await release.wait()
        return "Xong."

    monkeypatch.setattr(gemini, "summarize", slow)
    await run_turns(9)
    resp = await asyncio.wait_for(handle_chat("s", message="lượt 10"), timeout=2)
    assert resp.reply == "ok?"
    snap = await store.snapshot("s")
    assert snap.summary == "" and snap.summarized_count == 0
    release.set()
    await memory.drain()
    assert (await store.snapshot("s")).summary == "Xong."


async def test_only_one_summary_task_per_session(gemini_key, monkeypatch):
    release = asyncio.Event()
    calls = []

    async def slow(previous, turns):
        calls.append(1)
        await release.wait()
        return "Xong."

    monkeypatch.setattr(gemini, "summarize", slow)
    await run_turns(12)
    assert len(calls) == 1
    release.set()
    await memory.drain()


async def test_no_gemini_key_means_no_summary(set_env, monkeypatch):
    set_env(GEMINI_API_KEY="")
    called = []

    async def fake(previous, turns):
        called.append(1)
        return "x"

    monkeypatch.setattr(gemini, "summarize", fake)
    await run_turns(12)
    await memory.drain()
    assert called == []
    history = await memory.build_history("s")
    assert len(history) == 24  # chưa tóm tắt: 12 lượt nằm trong trần 14
    assert not history[0]["content"].startswith(memory.CONTEXT_MARKER)


async def test_summary_failure_keeps_old_summary_and_retries(gemini_key, monkeypatch):
    outcomes = ["Bản một.", gemini.GeminiError("HTTP 429"), "Bản hai."]
    seen_previous = []

    async def flaky(previous, turns):
        seen_previous.append(previous)
        out = outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.setattr(gemini, "summarize", flaky)
    await run_turns(10)
    await memory.drain()
    await run_turns(4, start=11)  # đủ ngưỡng lần hai: lỗi
    await memory.drain()
    snap = await store.snapshot("s")
    assert snap.summary == "Bản một." and snap.summarized_count == 4
    resp = await handle_chat("s", message="lượt 15")  # lượt sau thử lại
    assert resp.reply == "ok?"
    await memory.drain()
    snap = await store.snapshot("s")
    assert snap.summary == "Bản hai." and snap.summarized_count == 8
    assert seen_previous == ["", "Bản một.", "Bản một."]


async def test_summary_timeout_keeps_state(gemini_key, set_env, monkeypatch):
    set_env(SUMMARY_TIMEOUT="0.05")

    async def hang(previous, turns):
        await asyncio.sleep(5)
        return "muộn"

    monkeypatch.setattr(gemini, "summarize", hang)
    await run_turns(10)
    await memory.drain()
    snap = await store.snapshot("s")
    assert snap.summary == "" and snap.summarized_count == 0
    assert snap.unsummarized == 10


async def test_summary_for_deleted_session_is_dropped(gemini_key, monkeypatch):
    release = asyncio.Event()

    async def slow(previous, turns):
        await release.wait()
        return "Muộn."

    monkeypatch.setattr(gemini, "summarize", slow)
    await run_turns(10)
    store.clear()
    release.set()
    await memory.drain()
    snap = await store.snapshot("s")
    assert snap.summary == "" and snap.total == 0


async def test_gemini_429_during_summary_keeps_chat_working(gemini_key):
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(GEMINI_URL.format("gem-test")).respond(429, json={})
        await run_turns(10)
        await memory.drain()
        assert route.called
        snap = await store.snapshot("s")
        assert snap.summary == "" and snap.summarized_count == 0
        resp = await handle_chat("s", message="vẫn chạy chứ")
        assert resp.reply == "ok?"


# --- gemini.summarize ---


async def test_summarize_payload_truncation_and_safety_placeholder(gemini_key, set_env):
    set_env(SUMMARY_MAX_WORDS=5)
    turns = [
        turn(1),
        SessionTurn(
            turn_id="x",
            user_text="chi tiết nhạy cảm",
            reply="LỜI RIÊNG TƯ",
            safety=True,
            created_at="t",
        ),
    ]
    reply = {"candidates": [{"content": {"parts": [{"text": "một hai ba bốn năm sáu bảy tám"}]}}]}
    with respx.mock() as mock:
        route = mock.post(GEMINI_URL.format("gem-test")).respond(200, json=reply)
        result = await gemini.summarize("Bản cũ.", turns)
    assert result == "một hai ba bốn năm"
    request = route.calls.last.request
    assert request.headers["x-goog-api-key"] == KEY and KEY not in str(request.url)
    body = json.loads(request.read())
    text = body["contents"][0]["parts"][0]["text"]
    assert "Bản cũ." in text and "hỏi 1" in text
    assert "chi tiết nhạy cảm" not in text and "LỜI RIÊNG TƯ" not in text
    assert gemini.SAFETY_TURN_PLACEHOLDER in text
    assert "5 từ" in body["systemInstruction"]["parts"][0]["text"]


async def test_summarize_errors_raise_gemini_error_without_key(gemini_key):
    with respx.mock() as mock:
        route = mock.post(GEMINI_URL.format("gem-test"))
        route.respond(400, json={"error": {"message": f"bad key {KEY}"}})
        with pytest.raises(gemini.GeminiError) as info:
            await gemini.summarize("", [turn(1)])
        assert KEY not in str(info.value)
        route.mock(side_effect=httpx.ReadTimeout("slow"))
        with pytest.raises(gemini.GeminiError) as info:
            await gemini.summarize("", [turn(1)])
        assert KEY not in str(info.value)
        route.mock(return_value=httpx.Response(200, json={"candidates": []}))
        with pytest.raises(gemini.GeminiError):
            await gemini.summarize("", [turn(1)])
