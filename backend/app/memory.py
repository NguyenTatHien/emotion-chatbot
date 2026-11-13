"""Bộ nhớ hội thoại trong một cuộc trò chuyện: dựng `history` cho LLM và tóm tắt nền.

`history` gửi LLM gồm (1) cặp tin bối cảnh (bản tóm tắt + hồ sơ nhạc), chỉ khi có nội dung,
rồi (2) các lượt chưa được tóm tắt, nguyên văn. Backend là nơi duy nhất quyết định độ dài.
Tóm tắt chạy ở nền bằng Gemini, sau khi đã trả lời người dùng; lỗi chỉ ghi log.
"""

import asyncio
import logging

from app import gemini
from app.config import get_settings
from app.schemas import SessionTurn
from app.session import MemorySnapshot, SessionState, store

logger = logging.getLogger("emotion_chatbot.memory")

CONTEXT_MARKER = "[BỐI CẢNH CUỘC TRÒ CHUYỆN"
CONTEXT_HEADER = (
    f"{CONTEXT_MARKER} — tóm tắt các lượt trước, không phải tin nhắn mới]"
)
CONTEXT_ACK = "Mình nhớ rồi."
MAX_MUSIC_PROFILE_TURNS = 5

_RATING_VI = {"up": "thích", "down": "không thích"}

# Tác vụ tóm tắt nền; giữ tham chiếu để không bị thu gom rác giữa chừng.
_tasks: set[asyncio.Task] = set()


def _music_profile(snap: MemorySnapshot) -> str:
    """Hồ sơ nhạc từ MỌI lượt có bài (kể cả đã tóm tắt), tối đa 5 lượt gần nhất."""
    entries = [
        (snap.first_index + i + 1, turn)
        for i, turn in enumerate(snap.turns)
        if turn.songs
    ][-MAX_MUSIC_PROFILE_TURNS:]
    parts = []
    for number, turn in entries:
        songs = ", ".join(f"{s.title} – {s.artist}" for s in turn.songs)
        rating = f" (người dùng: {_RATING_VI[turn.rating]})" if turn.rating else ""
        parts.append(f"lượt {number}: {songs}{rating}")
    return "; ".join(parts)


def _context_message(snap: MemorySnapshot) -> str | None:
    lines = []
    if snap.summary.strip():
        lines.append(f"Tóm tắt: {snap.summary.strip()}")
    profile = _music_profile(snap)
    if profile:
        lines.append(f"Nhạc đã gợi ý: {profile}")
    if not lines:
        return None
    return "\n".join([CONTEXT_HEADER, *lines])


def history_from_snapshot(snap: MemorySnapshot) -> list[dict]:
    settings = get_settings()
    cap = settings.HISTORY_TURNS + 2 * settings.SUMMARY_BATCH_TURNS

    history: list[dict] = []
    context = _context_message(snap)
    if context:
        history.append({"role": "user", "content": context})
        history.append({"role": "assistant", "content": CONTEXT_ACK})

    start = max(snap.summarized_count, snap.first_index) - snap.first_index
    verbatim = snap.turns[start:][-cap:] if cap > 0 else []
    for turn in verbatim:
        history.append({"role": "user", "content": turn.user_text})
        history.append({"role": "assistant", "content": turn.reply})
    return history


async def build_history(session_id: str) -> list[dict]:
    """Lịch sử gửi LLM cho lượt kế tiếp của phiên: [cặp bối cảnh] + lượt chưa tóm tắt."""
    return history_from_snapshot(await store.snapshot(session_id))


async def maybe_schedule_summary(session_id: str) -> None:
    """Tạo tác vụ tóm tắt nền nếu đủ ngưỡng, có khoá Gemini và phiên chưa có tác vụ nào."""
    settings = get_settings()
    if not settings.GEMINI_API_KEY.strip():
        return
    snap = await store.snapshot(session_id)
    if snap.unsummarized < settings.HISTORY_TURNS + settings.SUMMARY_BATCH_TURNS:
        return
    state = await store.begin_summary(session_id)
    if state is None:
        return
    task = asyncio.create_task(_run_summary(session_id, state))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _run_summary(session_id: str, state: SessionState) -> None:
    settings = get_settings()
    new_summary: str | None = None
    new_count: int | None = None
    try:
        snap = await store.snapshot(session_id)
        start = max(snap.summarized_count, snap.first_index)
        offset = start - snap.first_index
        batch: list[SessionTurn] = snap.turns[offset : offset + settings.SUMMARY_BATCH_TURNS]
        if batch:
            new_summary = await asyncio.wait_for(
                gemini.summarize(snap.summary, batch), settings.SUMMARY_TIMEOUT
            )
            new_count = start + len(batch)
    except Exception as exc:  # noqa: BLE001 - tóm tắt lỗi không được làm hỏng cuộc trò chuyện
        logger.warning("Tóm tắt phiên lỗi, giữ bản cũ: %r", exc)
        new_summary = new_count = None
    finally:
        await store.finish_summary(session_id, state, new_summary, new_count)


async def drain() -> None:
    """Chờ mọi tác vụ tóm tắt đang chạy xong (dùng trong test)."""
    while _tasks:
        await asyncio.gather(*list(_tasks), return_exceptions=True)
