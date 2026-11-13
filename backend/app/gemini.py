"""Dự phòng sinh câu trả lời bằng Gemini API (REST `generateContent`, không dùng SDK).

Khoá API chỉ nằm trong header `x-goog-api-key`; thông điệp lỗi không bao giờ chứa nó.
"""

import logging

import httpx

from app.config import get_settings
from app.schemas import SessionTurn

logger = logging.getLogger("emotion_chatbot.gemini")

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = (
    "Bạn là một người bạn đồng hành biết lắng nghe, trò chuyện bằng tiếng Việt. "
    "Hãy trả lời đồng cảm, ấm áp và ngắn gọn (2–4 câu), phản ánh lại cảm xúc của người dùng "
    "rồi kết thúc bằng một câu hỏi mở để họ chia sẻ thêm. "
    "Không chẩn đoán bệnh hay rối loạn tâm lý, không kê đơn, không đưa ra lời khuyên y tế. "
    "Không nói rằng bạn là con người.\n"
    "Dòng đầu tiên của câu trả lời bắt buộc là [NHAC:CO] hoặc [NHAC:KHONG], "
    "sau đó xuống dòng rồi mới trả lời.\n"
    "- [NHAC:CO] khi người dùng muốn nghe nhạc / hỏi bài hát, hoặc đang buồn, lo âu, "
    "căng thẳng kéo dài và nghe nhạc có thể giúp họ dịu lại; không chọn CO nếu vừa gợi ý "
    "nhạc ở lượt ngay trước hoặc người dùng đã nói không muốn nghe nhạc.\n"
    "- [NHAC:KHONG] với chào hỏi, cảm ơn, hỏi thông tin, trò chuyện thường, "
    "hoặc khi đang kể dở chuyện.\n"
    "Không nhắc tới thẻ này hay tự liệt kê bài hát trong câu trả lời.\n"
    "Đoạn bắt đầu bằng [BỐI CẢNH CUỘC TRÒ CHUYỆN] là tóm tắt các lượt trước, "
    "không phải tin nhắn mới."
)

SUMMARY_SYSTEM_PROMPT = (
    "Bạn tóm tắt cuộc trò chuyện giữa một người dùng và một chatbot đồng hành bằng tiếng Việt. "
    "Gộp bản tóm tắt cũ (nếu có) với các lượt mới thành MỘT bản tóm tắt mới, "
    "tối đa {max_words} từ, viết thành văn xuôi ngắn gọn. "
    "Chỉ ghi những điều người dùng đã nói hoặc đã chia sẻ (chuyện gì, cảm xúc, mong muốn, "
    "điều họ thích hay không thích); không suy diễn, không bịa, không chẩn đoán. "
    "Chỉ trả về nội dung bản tóm tắt, không thêm lời dẫn."
)
SAFETY_TURN_PLACEHOLDER = "(lượt có nội dung nhạy cảm; bot đã gửi thông điệp hỗ trợ)"

_AROUSAL_VI = {"low": "thấp", "medium": "trung bình", "high": "cao"}
_GOAL_VI = {
    "xoa_diu": "muốn được xoa dịu",
    "nang_mood": "muốn nâng tinh thần",
    "tap_trung": "muốn tập trung",
    "giai_toa": "muốn giải toả",
}


class GeminiError(Exception):
    """Lỗi gọi Gemini; thông điệp chỉ gồm mã HTTP hoặc loại lỗi, không chứa khoá."""


def build_payload(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None,
) -> dict:
    contents = [
        {
            "role": "model" if m.get("role") == "assistant" else "user",
            "parts": [{"text": str(m.get("content", ""))}],
        }
        for m in history
    ]
    notes = [f"Cảm xúc nhận diện được: {(emotion or {}).get('label', 'Other')}"]
    if arousal in _AROUSAL_VI:
        notes.append(f"mức kích động trong giọng nói: {_AROUSAL_VI[arousal]}")
    if goal in _GOAL_VI:
        notes.append(f"người dùng {_GOAL_VI[goal]} bằng âm nhạc")
    user_part = f"[{'; '.join(notes)}]\n{text}"
    contents.append({"role": "user", "parts": [{"text": user_part}]})
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1024},
    }


def _extract_text(data: object) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]  # type: ignore[index]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError, TypeError, AttributeError):
        raise GeminiError("phản hồi không có nội dung") from None
    text = text.strip()
    if not text:
        raise GeminiError("phản hồi rỗng")
    return text


async def _post(payload: dict, timeout: float) -> object:
    """Gọi generateContent, trả JSON; lỗi mạng/HTTP -> GeminiError (hoặc TimeoutError)."""
    settings = get_settings()
    url = ENDPOINT.format(model=settings.GEMINI_MODEL)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url, json=payload, headers={"x-goog-api-key": settings.GEMINI_API_KEY}
            )
    except httpx.TimeoutException:
        raise TimeoutError("Gemini quá thời gian") from None
    except httpx.HTTPError as exc:
        raise GeminiError(type(exc).__name__) from None
    if response.status_code != 200:
        raise GeminiError(f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise GeminiError("phản hồi không phải JSON") from None


async def generate_reply(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None = None,
) -> str:
    settings = get_settings()
    payload = build_payload(text, emotion, arousal, history, goal)
    return _extract_text(await _post(payload, settings.GEMINI_TIMEOUT))


def _turn_lines(index: int, turn: SessionTurn) -> str:
    if turn.safety:
        return f"[Lượt {index}] {SAFETY_TURN_PLACEHOLDER}"
    return f"[Lượt {index}] Người dùng: {turn.user_text}\nBot: {turn.reply}"


def build_summary_payload(previous_summary: str, turns: list[SessionTurn]) -> dict:
    settings = get_settings()
    previous = previous_summary.strip() or "(chưa có)"
    body = "\n".join(_turn_lines(i, t) for i, t in enumerate(turns, start=1))
    user_part = f"Bản tóm tắt cũ: {previous}\n\nCác lượt mới:\n{body}"
    return {
        "systemInstruction": {
            "parts": [{"text": SUMMARY_SYSTEM_PROMPT.format(max_words=settings.SUMMARY_MAX_WORDS)}]
        },
        "contents": [{"role": "user", "parts": [{"text": user_part}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }


def _limit_words(text: str, max_words: int) -> str:
    words = text.split()
    if max_words <= 0 or len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words])


async def summarize(previous_summary: str, turns: list[SessionTurn]) -> str:
    """Gộp bản tóm tắt cũ với các lượt mới thành bản tóm tắt mới (tối đa SUMMARY_MAX_WORDS từ).

    Lượt `safety=True` được thay bằng một câu trung tính. Mọi lỗi đều raise `GeminiError`
    với thông điệp không chứa khoá API.
    """
    settings = get_settings()
    payload = build_summary_payload(previous_summary, turns)
    try:
        data = await _post(payload, settings.SUMMARY_TIMEOUT)
    except TimeoutError:
        raise GeminiError("tóm tắt quá thời gian") from None
    return _limit_words(_extract_text(data), settings.SUMMARY_MAX_WORDS)
