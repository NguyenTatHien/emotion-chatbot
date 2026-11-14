import asyncio
import time

import pytest
from pydantic import ValidationError

from app import registry
from app.config import Settings
from app.pipeline import handle_chat, try_call
from app.session import SessionStore


def test_default_mode_is_mock():
    assert registry.mode_of("emotion") == "mock"
    assert registry.get("emotion").__module__ == "mocks.emotion"


def test_per_module_override_beats_model_mode(set_env):
    set_env(MODEL_MODE="mock", MUSIC_MODE="local")
    assert registry.get("music").__module__ == "modules.music"
    for name in ("emotion", "speech", "safety", "llm"):
        assert registry.get(name).__module__ == f"mocks.{name}"


def test_model_mode_applies_to_all(set_env):
    set_env(MODEL_MODE="local")
    names = ("emotion", "speech", "safety", "llm", "music")
    assert all(registry.mode_of(n) == "local" for n in names)


def test_invalid_mode_rejected():
    with pytest.raises(ValidationError, match="EMOTION_MODE"):
        Settings(EMOTION_MODE="gpu")


def test_remote_modules_use_model_server_client(set_env):
    set_env(MODEL_MODE="mock", EMOTION_MODE="remote", LLM_MODE="remote", SPEECH_MODE="remote")
    assert registry.get("emotion").__module__ == "app.clients.model_server"
    assert registry.get("llm").__module__ == "app.clients.model_server"
    assert registry.get("speech", "transcribe").__name__ == "transcribe"
    assert registry.get("speech", "extract_prosody").__name__ == "extract_prosody"


def test_remote_not_available_for_safety_and_music(set_env):
    set_env(SAFETY_MODE="remote", MUSIC_MODE="remote")
    for name in ("safety", "music"):
        with pytest.raises(registry.RemoteNotConfigured):
            registry.get(name)


def test_override_and_reset():
    registry.override("emotion", lambda text: {"label": "Other", "probs": {}})
    assert registry.get("emotion")("x")["label"] == "Other"
    registry.reset_overrides()
    assert registry.get("emotion").__module__ == "mocks.emotion"


def test_override_unknown_function_rejected():
    with pytest.raises(KeyError):
        registry.override("emotion", lambda: None, func="nope")


async def test_try_call_ok_timeout_and_error():
    ok, warn = await try_call("emotion", lambda x: x + 1, 1, timeout=1)
    assert (ok, warn) == (2, None)

    def boom():
        raise ValueError("x")

    res, warn = await try_call("emotion", boom, timeout=1)
    assert res is None and "emotion" in warn

    res, warn = await try_call("llm", time.sleep, 0.5, timeout=0.05)
    assert res is None and "llm" in warn


async def test_history_is_capped_by_backend(set_env):
    """Không có khoá Gemini nên không có tóm tắt: trần = HISTORY_TURNS + 2*SUMMARY_BATCH_TURNS."""
    seen = {}

    def spy(text, emotion, arousal, history, goal=None):
        seen["history"] = history
        return "ok?"

    registry.override("llm", spy)
    for i in range(8):
        await handle_chat("s1", message=f"lượt {i}")
    assert len(seen["history"]) == 2 + 14  # cặp bối cảnh + đủ 7 lượt trước, chưa chạm trần
    for i in range(8, 20):
        await handle_chat("s1", message=f"lượt {i}")
    history = seen["history"]
    assert len(history) == 2 + 2 * (6 + 2 * 4)
    assert history[2] == {"role": "user", "content": "lượt 5"}
    assert history[-2]["content"] == "lượt 18"
    assert [m["role"] for m in history[:4]] == ["user", "assistant"] * 2


async def test_history_turns_setting(set_env):
    set_env(HISTORY_TURNS=2, SUMMARY_BATCH_TURNS=1)
    seen = {}

    def spy(text, emotion, arousal, history, goal=None):
        seen["n"] = len(history)
        return "ok?"

    registry.override("llm", spy)
    for i in range(8):
        await handle_chat("s1", message=f"lượt {i}")
    assert seen["n"] == 2 + 2 * (2 + 2 * 1)


async def test_chip_runs_music_first_and_llm_sees_the_songs():
    """Có chip: chọn bài trước, ghi vào ghi chú bối cảnh để câu trả lời giới thiệu đúng bài."""
    order, seen = [], {}

    def llm(text, emotion, arousal, history, goal=None):
        order.append("llm")
        seen["note"] = history[0]["content"]
        return "Mình mở Kiss the Rain trước nhé."

    def music(label, arousal, goal, k=5, exclude=None):
        order.append("music")
        song = {"title": "Kiss the Rain", "artist": "Yiruma", "youtube_url": "https://x"}
        return [{**song, "reason": "r"}]

    registry.override("llm", llm)
    registry.override("music", music)
    resp = await handle_chat("s1", message="giờ mình cần học bài", goal="tap_trung")
    assert order == ["music", "llm"]
    assert "Bài sẽ gợi ý kèm câu trả lời: Kiss the Rain – Yiruma" in seen["note"]
    assert len(resp.songs) == 1
    assert resp.meta.analysis.music_lead == "Vài bài giúp bạn tập trung"


async def test_chip_music_failure_still_replies_without_note():
    seen = {}

    def llm(text, emotion, arousal, history, goal=None):
        seen["note"] = history[0]["content"]
        return "ok?"

    def broken(*a, **k):
        raise RuntimeError("hỏng")

    registry.override("llm", llm)
    registry.override("music", broken)
    resp = await handle_chat("s1", message="mình buồn", goal="xoa_diu")
    assert resp.reply == "ok?"
    assert resp.songs == []
    assert "Bài sẽ gợi ý" not in seen["note"]
    assert resp.meta.analysis.music_lead is None


async def test_music_runs_before_llm_when_user_asks():
    order = []

    def llm(*a, **k):
        order.append("llm")
        time.sleep(0.1)
        return "[NHAC:CO]\nmình nghe bạn?"

    def music(label, arousal, goal, k=5, exclude=None):
        order.append("music")
        return []  # music trả rỗng → fallback luồng LLM; guard chấp nhận (user xin nhạc)

    registry.override("llm", llm)
    registry.override("music", music)
    resp = await handle_chat("s1", message="mình buồn, mở nhạc gì nghe đi")
    # Route-fix: user xin nhạc → backend chọn bài TRƯỚC (RAG retrieve-then-generate);
    # music rỗng → LLM fallback và guard quyết định (music_flag được check, cũ bị bỏ).
    assert order == ["music", "llm", "music"]
    assert resp.meta.music_decision == "llm"


async def test_route_music_template_when_module_has_songs():
    order = []

    def llm(*a, **k):
        order.append("llm")
        return "KHÔNG ĐƯỢC GỌI"

    def music(label, arousal, goal, k=5, exclude=None):
        order.append("music")
        return [{"title": "Nàng Thơ", "artist": "Trịnh Đình Quang", "youtube_url": "https://y/1"}]

    registry.override("llm", llm)
    registry.override("music", music)
    resp = await handle_chat("s2", message="đề xuất cho mình vài bài nhạc nha")
    assert order == ["music"]  # template — LLM KHÔNG được gọi (hallucination by construction)
    assert resp.meta.music_decision == "request"
    assert resp.meta.llm_backend == "template"
    assert resp.reply.startswith("Mình chọn sẵn 1 bài")


async def test_session_store_limits():
    from app.schemas import SessionTurn

    def turn(i):
        return SessionTurn(turn_id=str(i), user_text="u", reply="r", created_at="t")

    store = SessionStore(max_turns=3, max_sessions=2)
    for i in range(5):
        await store.append_turn("a", turn(i))
    assert [t.turn_id for t in await store.get_turns("a")] == ["2", "3", "4"]
    await store.append_turn("b", turn(0))
    await store.append_turn("c", turn(0))  # đẩy phiên cũ nhất ("a") ra
    assert await store.get_turns("a") == []
    assert len(await store.get_turns("b")) == 1


async def test_try_call_supports_async_functions():
    async def fine(x):
        return x * 2

    async def slow():
        await asyncio.sleep(0.5)

    assert await try_call("emotion", fine, 2, timeout=1) == (4, None)
    res, warn = await try_call("emotion", slow, timeout=0.05)
    assert res is None and "quá thời gian" in warn
