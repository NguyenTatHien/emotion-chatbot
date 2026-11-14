"""Bộ nhớ hội thoại trong một cuộc trò chuyện: dựng `history` cho LLM và tóm tắt nền.

`history` gửi LLM gồm (1) cặp tin bối cảnh (dữ kiện: lượt thứ mấy, cảm xúc các lượt gần đây,
lần gợi ý nhạc gần nhất, giọng điệu nên dùng; cộng bản tóm tắt và hồ sơ nhạc nếu có), có từ
lượt đầu tiên khi đã có giọng điệu, rồi (2) các lượt chưa được tóm tắt, nguyên văn.
Backend là nơi duy nhất quyết định độ dài.
Tóm tắt chạy ở nền bằng Gemini, sau khi đã trả lời người dùng; lỗi chỉ ghi log.
"""

import asyncio
import logging

from app import gemini
from app.config import get_settings
from app.constants import LABELS_VI
from app.schemas import SessionTurn
from app.session import MemorySnapshot, SessionState, store

logger = logging.getLogger("emotion_chatbot.memory")

CONTEXT_MARKER = "[BỐI CẢNH CUỘC TRÒ CHUYỆN"
CONTEXT_HEADER = (
    f"{CONTEXT_MARKER} — ghi chú của hệ thống về các lượt trước, không phải tin nhắn mới]"
)
CONTEXT_ACK = "Mình nhớ rồi."
MAX_MUSIC_PROFILE_TURNS = 5
RECENT_EMOTION_TURNS = 3
SAFETY_LABEL = "safety"
TONE_PREFIX = "Giọng điệu nên dùng:"

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


def recent_emotion_entries(snap: MemorySnapshot) -> list[tuple[int, str]]:
    """(số lượt, nhãn) của vài lượt gần nhất; lượt safety có nhãn `safety`."""
    entries = []
    for i, turn in list(enumerate(snap.turns))[-RECENT_EMOTION_TURNS:]:
        number = snap.first_index + i + 1
        if turn.safety:
            entries.append((number, SAFETY_LABEL))
        elif turn.emotion is not None:
            entries.append((number, turn.emotion.label))
    return entries


def last_music_turn(snap: MemorySnapshot) -> int | None:
    music_turns = [snap.first_index + i + 1 for i, t in enumerate(snap.turns) if t.songs]
    return music_turns[-1] if music_turns else None


def _recent_emotions(snap: MemorySnapshot) -> str:
    """Cảm xúc CafeBERT của vài lượt gần nhất, để LLM biết buồn đã kéo dài hay chưa."""
    parts = []
    for number, label in recent_emotion_entries(snap):
        name = "nội dung nhạy cảm" if label == SAFETY_LABEL else LABELS_VI.get(label, label)
        parts.append(f"lượt {number} {name}")
    return "; ".join(parts)


def _facts(snap: MemorySnapshot) -> list[str]:
    """Dữ kiện do backend tự đếm; LLM dùng để quyết định thẻ nhạc."""
    facts = [f"Tin nhắn sắp tới là lượt thứ {snap.total + 1} của người dùng."]
    emotions = _recent_emotions(snap)
    if emotions:
        facts.append(f"Cảm xúc các lượt gần đây: {emotions}.")
    last = last_music_turn(snap)
    if last is not None:
        facts.append(
            f"Lượt gần nhất có gợi ý nhạc: lượt {last} (cách đây {snap.total + 1 - last} lượt)."
        )
    else:
        facts.append("Chưa gợi ý nhạc lần nào.")
    return facts


def _context_message(snap: MemorySnapshot, tone_text: str | None) -> str | None:
    if snap.total == 0 and not tone_text:
        return None
    lines = _facts(snap)
    if snap.summary.strip():
        lines.append(f"Tóm tắt: {snap.summary.strip()}")
    profile = _music_profile(snap)
    if profile:
        lines.append(f"Nhạc đã gợi ý: {profile}")
    if tone_text:
        lines.append(f"{TONE_PREFIX} {tone_text}")
    return "\n".join([CONTEXT_HEADER, *lines])


def history_from_snapshot(snap: MemorySnapshot, tone_text: str | None = None) -> list[dict]:
    settings = get_settings()
    cap = settings.HISTORY_TURNS + 2 * settings.SUMMARY_BATCH_TURNS

    history: list[dict] = []
    context = _context_message(snap, tone_text)
    if context:
        history.append({"role": "user", "content": context})
        history.append({"role": "assistant", "content": CONTEXT_ACK})

    start = max(snap.summarized_count, snap.first_index) - snap.first_index
    verbatim = snap.turns[start:][-cap:] if cap > 0 else []
    for turn in verbatim:
        history.append({"role": "user", "content": turn.user_text})
        history.append({"role": "assistant", "content": turn.reply})
    return history


async def build_context(
    session_id: str, tone_text: str | None = None
) -> tuple[list[dict], MemorySnapshot]:
    """Lịch sử gửi LLM kèm đúng ảnh chụp bộ nhớ đã dùng để dựng nó (chỉ gọi snapshot một lần)."""
    snap = await store.snapshot(session_id)
    return history_from_snapshot(snap, tone_text), snap


async def build_history(session_id: str, tone_text: str | None = None) -> list[dict]:
    """Lịch sử gửi LLM cho lượt kế tiếp của phiên: [cặp bối cảnh] + lượt chưa tóm tắt.

    Cặp bối cảnh có khi phiên đã có lượt hoặc có `tone_text` (lượt đầu tiên).
    """
    return (await build_context(session_id, tone_text))[0]


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
