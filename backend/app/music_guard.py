"""Chốt chặn cho thẻ `[NHAC:CO]` của LLM.

LLM (nhất là Qwen3-4B) không phải lúc nào cũng làm đúng luật trong prompt: nó gợi ý nhạc ngay
lần đầu người dùng buồn, ngay sau lượt vừa gợi ý, hoặc ở câu bình thường. Backend có sẵn số
liệu đo được (cảm xúc CafeBERT từng lượt, lượt nào đã có nhạc) nên kiểm tra lại các luật đó.
LLM vẫn đề xuất; chốt chặn chỉ bỏ những lần CO trái luật, không bao giờ tự thêm nhạc.

Luật (xét theo thứ tự):
1. Người dùng xin nhạc → chấp nhận.
2. Lượt ngay trước vừa có nhạc → tạm nghỉ một lượt.
3. Cảm xúc đang chạy dự phòng (không có số liệu thật) → tin LLM.
4. Lượt này tiêu cực và lượt trước cũng tiêu cực (đã ≥ 2 lượt) → chấp nhận.
5. Lượt này tiêu cực nhưng là lần đầu → lắng nghe thêm trước.
6. Còn lại (Bình thường, Vui vẻ, Ngạc nhiên) → chưa phù hợp.
"""

import re

from app.fallbacks import strip_accents

NEGATIVE_LABELS = frozenset({"Sadness", "Fear", "Anger", "Disgust"})

# Lý do bị chặn: mã → câu hiển thị trong khung "Đã phân tích".
GUARD_REASONS: dict[str, str] = {
    "cooldown": "Vừa gợi ý nhạc ở lượt trước nên lượt này tạm nghỉ",
    "first": "Bot muốn lắng nghe thêm trước khi gợi ý nhạc",
    "neutral": "Bot định gợi ý nhạc nhưng lượt này chưa phù hợp",
}

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
    "bai nhac",        # "đề xuất cho mình 5 bài nhạc..." (thật từ E2E prod-chat test 2026-11-15)
    "ca khuc",
    "nhac gi",
    "nhac nao",
    "nghe gi",
    "de xuat nhac",    # "đề xuất ... nhạc"
    "de xuat bai",     # "đề xuất ... bài hát/bài nào đó"
    "playlist",
    "lofi",
    "nhac chill",
    "nhac nhe",
)
_REQUEST_RE = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in _REQUEST_PHRASES) + r")\b")


def asks_for_music(text: str) -> bool:
    """Người dùng có đang xin nhạc / hỏi bài hát không."""
    return bool(_REQUEST_RE.search(strip_accents((text or "").lower())))


def check_music_tag(
    text: str,
    label: str,
    emotion_source: str | None,
    prev_label: str | None = None,
    prev_had_music: bool = False,
) -> tuple[bool, str | None]:
    """Có chấp nhận thẻ CO của LLM ở lượt này không.

    Trả (chấp_nhận, mã_lý_do_bị_chặn). Mã nằm trong `GUARD_REASONS` khi bị chặn, None khi được.
    `prev_label` là nhãn cảm xúc (đã fusion) của lượt ngay trước, None nếu không có hoặc là
    lượt safety; `prev_had_music` cho biết lượt ngay trước đã có bài hát.
    """
    if asks_for_music(text):
        return True, None
    if prev_had_music:
        return False, "cooldown"
    if emotion_source != "module":
        return True, None
    if label in NEGATIVE_LABELS:
        if prev_label in NEGATIVE_LABELS:
            return True, None
        return False, "first"
    return False, "neutral"


def accept_music_tag(
    text: str,
    label: str,
    emotion_source: str | None,
    prev_label: str | None = None,
    prev_had_music: bool = False,
) -> bool:
    """Dạng rút gọn của `check_music_tag`: chỉ trả có chấp nhận hay không."""
    return check_music_tag(text, label, emotion_source, prev_label, prev_had_music)[0]
