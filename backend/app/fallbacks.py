"""Dự phòng khi module lỗi: cảm xúc mặc định, câu trả lời soạn sẵn, kiểm an toàn từ khóa."""

import unicodedata

from app.config import get_settings
from app.constants import LABELS

CANNED_REPLIES = {
    "Anger": (
        "Mình nghe được là bạn đang rất bực bội. "
        "Bạn muốn kể mình nghe điều gì đã xảy ra không?"
    ),
    "Disgust": (
        "Có vẻ có chuyện khiến bạn thấy khó chịu và không thoải mái. "
        "Bạn có muốn chia sẻ thêm không?"
    ),
    "Enjoyment": (
        "Nghe bạn có vẻ đang vui, mình cũng thấy vui lây. "
        "Điều gì làm bạn vui hôm nay vậy?"
    ),
    "Fear": "Mình hiểu là bạn đang lo lắng. Bạn đang băn khoăn điều gì nhất lúc này?",
    "Other": "Mình đang lắng nghe đây. Bạn muốn kể thêm về điều đang diễn ra không?",
    "Sadness": (
        "Mình rất tiếc khi nghe bạn đang buồn. "
        "Bạn có muốn kể mình nghe chuyện gì đã xảy ra không?"
    ),
    "Surprise": "Nghe có vẻ bất ngờ thật đấy. Chuyện gì vừa xảy ra vậy, bạn kể mình nghe nhé?",
}

_RISK_PHRASES = [
    "tự tử",
    "tự sát",
    "muốn chết",
    "không muốn sống",
    "không muốn tồn tại",
    "tự làm hại",
    "tự hại bản thân",
    "cắt tay",
    "kết liễu",
    "kết thúc cuộc đời",
    "chết đi cho rồi",
]


def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


_RISK_PLAIN = [strip_accents(p) for p in _RISK_PHRASES]


def fallback_emotion() -> dict:
    """Cảm xúc dự phòng: `Other` với xác suất đều."""
    p = 1.0 / len(LABELS)
    return {"label": "Other", "probs": {label: p for label in LABELS}}


def canned_reply(label: str | None) -> str:
    return CANNED_REPLIES.get(label or "Other", CANNED_REPLIES["Other"])


def keyword_safety(text: str) -> bool:
    """True nếu văn bản chứa cụm từ nguy hiểm (so khớp có dấu và không dấu)."""
    lowered = (text or "").lower()
    plain = strip_accents(lowered)
    if any(p in lowered for p in _RISK_PHRASES):
        return True
    return any(p in plain for p in _RISK_PLAIN)


def safety_message() -> str:
    """Thông điệp an toàn dự phòng; dòng hỗ trợ lấy từ SAFETY_HOTLINE_TEXT."""
    message = (
        "Mình rất lo cho bạn và muốn bạn được an toàn. Mình chỉ là một chatbot, không thay "
        "được người thật. Nếu bạn đang nghĩ đến việc làm hại bản thân, hãy nói ngay với một "
        "người bạn tin tưởng, người thân, hoặc liên hệ cơ sở y tế/đường dây hỗ trợ gần nhất. "
        "Nếu đang gặp nguy hiểm tức thì, hãy gọi cấp cứu hoặc nhờ người ở gần giúp bạn."
    )
    hotline = get_settings().SAFETY_HOTLINE_TEXT.strip()
    if hotline:
        message += "\n" + hotline
    return message
