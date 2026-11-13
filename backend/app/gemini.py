"""Dự phòng sinh câu trả lời bằng Gemini API (REST `generateContent`, không dùng SDK).

Khoá API chỉ nằm trong header `x-goog-api-key`; thông điệp lỗi không bao giờ chứa nó.
"""

import logging

import httpx

from app.config import get_settings
from app.constants import LABELS_VI
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
    "Chọn [NHAC:CO] chỉ khi:\n"
    "(1) người dùng xin nghe nhạc, hỏi bài hát hoặc nhờ gợi ý bài; hoặc\n"
    "(2) người dùng đã buồn, lo sợ hoặc tức giận rõ rệt ở ít nhất 2 lượt gần đây "
    "(tính cả lượt hiện tại) và lượt ngay trước chưa được gợi ý nhạc.\n"
    "Mọi trường hợp khác chọn [NHAC:KHONG], nhất là: lượt đầu tiên; lần đầu kể một chuyện "
    "(hãy lắng nghe trước); cảm xúc Bình thường hoặc Vui vẻ; chào hỏi, cảm ơn, hỏi thông tin; "
    "người dùng đã nói không muốn nghe nhạc.\n"
    "Nếu đầu lịch sử không có ghi chú của hệ thống thì đây là lượt đầu tiên.\n"
    "Ví dụ:\n"
    '"chào bạn" → [NHAC:KHONG]\n'
    '"mình đang phân vân về đề án tốt nghiệp" → [NHAC:KHONG]\n'
    '"có bài nào nghe cho vui không" → [NHAC:CO]\n'
    'lượt thứ 3, hai lượt trước đều buồn: "mình sợ rớt môn lắm, chán ghê" → [NHAC:CO]\n'
    "Không nhắc tới thẻ này hay tự liệt kê bài hát trong câu trả lời.\n"
    "Chỉ viết lời nói trực tiếp với người dùng, không viết nhận xét hay tóm tắt về họ."
)

# Chỉ thêm khi lịch sử thật sự mở đầu bằng ghi chú bối cảnh: nhắc tới nhãn ở mọi lượt khiến
# mô hình nhỏ chép lại nhãn và tự viết "tóm tắt" vào câu trả lời.
CONTEXT_NOTE = (
    "Tin nhắn đầu tiên trong lịch sử là ghi chú của hệ thống (lượt thứ mấy, cảm xúc các lượt "
    "gần đây, lần gợi ý nhạc gần nhất, tóm tắt), không phải lời người dùng. Dùng nó để chọn thẻ "
    "nhạc và hiểu bối cảnh; không chép lại, không nhắc tới và không tự viết tóm tắt trong câu "
    "trả lời."
)
_CONTEXT_PREFIX = "[BỐI CẢNH"


def has_context_pair(history: list[dict]) -> bool:
    """Lịch sử có mở đầu bằng cặp tin bối cảnh do `app/memory.py` dựng không."""
    if not history:
        return False
    return str(history[0].get("content", "")).lstrip().startswith(_CONTEXT_PREFIX)


def emotion_note(emotion: object) -> str:
    """'Bình thường (73%)': tên tiếng Việt của nhãn kèm xác suất của nhãn đó (nếu có)."""
    if not isinstance(emotion, dict):
        return LABELS_VI.get(str(emotion or "Other"), str(emotion or "Other"))
    label = str(emotion.get("label", "Other"))
    name = LABELS_VI.get(label, label)
    prob = (emotion.get("probs") or {}).get(label)
    try:
        return f"{name} ({float(prob):.0%})" if prob is not None else name
    except (TypeError, ValueError):
        return name


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
    notes = [f"Cảm xúc lượt hiện tại: {emotion_note(emotion)}"]
    if arousal in _AROUSAL_VI:
        notes.append(f"mức kích động trong giọng nói: {_AROUSAL_VI[arousal]}")
    if goal in _GOAL_VI:
        notes.append(f"người dùng {_GOAL_VI[goal]} bằng âm nhạc")
    user_part = f"[{'; '.join(notes)}]\n{text}"
    contents.append({"role": "user", "parts": [{"text": user_part}]})
    system = f"{SYSTEM_PROMPT}\n{CONTEXT_NOTE}" if has_context_pair(history) else SYSTEM_PROMPT
    return {
        "systemInstruction": {"parts": [{"text": system}]},
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
