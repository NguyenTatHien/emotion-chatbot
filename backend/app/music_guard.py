"""Chốt chặn cho thẻ `[NHAC:CO]` của LLM.

LLM (nhất là Qwen3-4B) đôi khi gợi ý nhạc ở lượt không phù hợp, ví dụ một câu giới thiệu
bình thường ngay sau vài lượt buồn. Backend chỉ chấp nhận thẻ CO khi lượt hiện tại có lý do
rõ ràng: người dùng xin nhạc, hoặc cảm xúc lượt này là tiêu cực. LLM vẫn là bên quyết định;
chốt chặn chỉ bỏ những lần CO sai rõ ràng, không bao giờ tự thêm nhạc.
"""

import re

from app.fallbacks import strip_accents

NEGATIVE_LABELS = frozenset({"Sadness", "Fear", "Anger", "Disgust"})

# Cụm xin nhạc, so khớp trên chữ thường đã bỏ dấu (người dùng hay gõ không dấu).
_REQUEST_PHRASES = (
    "nghe nhac",
    "mo nhac",
    "bat nhac",
    "goi y nhac",
    "goi y bai",
    "bai hat",
    "bai nao",
    "bai gi",
    "ca khuc",
    "nhac gi",
    "nhac nao",
    "nghe gi",
    "playlist",
    "lofi",
    "nhac chill",
    "nhac nhe",
)
_REQUEST_RE = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in _REQUEST_PHRASES) + r")\b")


def asks_for_music(text: str) -> bool:
    """Người dùng có đang xin nhạc / hỏi bài hát không."""
    return bool(_REQUEST_RE.search(strip_accents((text or "").lower())))


def accept_music_tag(text: str, label: str, emotion_source: str | None) -> bool:
    """Có chấp nhận thẻ CO của LLM ở lượt này không.

    - Người dùng xin nhạc: chấp nhận.
    - Cảm xúc lượt này (đã qua fusion) là Buồn/Lo sợ/Tức giận/Khó chịu: chấp nhận.
    - Cảm xúc đang chạy dự phòng (không có thông tin thật): tin quyết định của LLM.
    - Còn lại (Bình thường, Vui vẻ, Ngạc nhiên mà không xin nhạc): bỏ thẻ CO.
    """
    if asks_for_music(text):
        return True
    if emotion_source != "module":
        return True
    return label in NEGATIVE_LABELS
