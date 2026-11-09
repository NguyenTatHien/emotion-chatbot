"""Dự phòng sinh câu trả lời bằng Gemini API (REST `generateContent`, không dùng SDK).

Khoá API chỉ nằm trong header `x-goog-api-key`; thông điệp lỗi không bao giờ chứa nó.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("emotion_chatbot.gemini")

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_HISTORY_MESSAGES = 12  # 6 lượt = 12 tin (người dùng + bot)

SYSTEM_PROMPT = (
    "Bạn là một người bạn đồng hành biết lắng nghe, trò chuyện bằng tiếng Việt. "
    "Hãy trả lời đồng cảm, ấm áp và ngắn gọn (2–4 câu), phản ánh lại cảm xúc của người dùng "
    "rồi kết thúc bằng một câu hỏi mở để họ chia sẻ thêm. "
    "Không chẩn đoán bệnh hay rối loạn tâm lý, không kê đơn, không đưa ra lời khuyên y tế. "
    "Không nói rằng bạn là con người."
)

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
        for m in history[-MAX_HISTORY_MESSAGES:]
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


async def generate_reply(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None = None,
) -> str:
    settings = get_settings()
    url = ENDPOINT.format(model=settings.GEMINI_MODEL)
    payload = build_payload(text, emotion, arousal, history, goal)
    try:
        async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT) as client:
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
        data = response.json()
    except ValueError:
        raise GeminiError("phản hồi không phải JSON") from None
    return _extract_text(data)
