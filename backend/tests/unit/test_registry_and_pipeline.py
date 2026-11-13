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
    assert len(seen["history"]) == 14  # lượt thứ 8 thấy đủ 7 lượt trước, chưa chạm trần
    for i in range(8, 20):
        await handle_chat("s1", message=f"lượt {i}")
    history = seen["history"]
    assert len(history) == 2 * (6 + 2 * 4)
    assert history[0] == {"role": "user", "content": "lượt 5"}
    assert history[-2]["content"] == "lượt 18"
    assert [m["role"] for m in history[:2]] == ["user", "assistant"]


async def test_history_turns_setting(set_env):
    set_env(HISTORY_TURNS=2, SUMMARY_BATCH_TURNS=1)
    seen = {}

    def spy(text, emotion, arousal, history, goal=None):
        seen["n"] = len(history)
        return "ok?"

    registry.override("llm", spy)
    for i in range(8):
        await handle_chat("s1", message=f"lượt {i}")
    assert seen["n"] == 2 * (2 + 2 * 1)


async def test_llm_and_music_run_in_parallel():
    def slow_llm(*a, **k):
        time.sleep(0.3)
        return "xin chào?"

    def slow_music(label, arousal, goal, k=5):
        time.sleep(0.3)
        return [{"title": "t", "artist": "a", "youtube_url": "https://x", "reason": "r"}]

    registry.override("llm", slow_llm)
    registry.override("music", slow_music)
    start = time.perf_counter()
    resp = await handle_chat("s1", message="mình buồn", goal="xoa_diu")
    elapsed = time.perf_counter() - start
    assert elapsed < 0.55
    assert resp.meta.latency_ms < 550
    assert len(resp.songs) == 1


async def test_music_runs_after_llm_without_chip():
    order = []

    def llm(*a, **k):
        order.append("llm")
        time.sleep(0.1)
        return "[NHAC:CO]\nmình nghe bạn?"

    def music(label, arousal, goal, k=5):
        order.append("music")
        return []

    registry.override("llm", llm)
    registry.override("music", music)
    resp = await handle_chat("s1", message="mình buồn")
    assert order == ["llm", "music"]
    assert resp.meta.music_decision == "llm"


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
