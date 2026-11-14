"""Tách thẻ điều khiển nhạc `[NHAC:CO]` / `[NHAC:KHONG]` khỏi câu trả lời của LLM.

Thẻ chỉ được đọc từ câu trả lời của LLM (không bao giờ từ tin nhắn người dùng) và
không được lọt ra màn hình, nên bộ tách chấp nhận nhiều biến thể: có hoặc không dấu,
hoa hoặc thường, khoảng trắng quanh dấu `:`, dạng có ngoặc vuông ở bất kỳ vị trí nào
và dạng không ngoặc khi đứng riêng một dòng.
"""

import re
import unicodedata

# Mỗi lớp ký tự gồm chữ gốc và mọi biến thể dấu tiếng Việt (đã ở dạng NFC).
_A = "aàáảãạăằắẳẵặâầấẩẫậ"
_O = "oòóỏõọôồốổỗộơờớởỡợ"

_NHAC = rf"nh[{_A}]c"


def _value(name: str) -> str:
    return rf"(?P<{name}>c[{_O}]|kh[{_O}]ng)"


# Model nhỏ đôi khi nhại few-shot ví dụ và sinh thẻ bể dạng `[M NHAC:KHONG]`,
# `[MNHAC:KHONG]` — cho phép ≤3 ký tự nhiễu giữa `[` và chữ NHAC (chữ/số, có/không
# khoảng trắng), giữ mọi biến thể cũ.
_BRACKETED = rf"\[\s*\w{{0,3}}\s*{_NHAC}\s*[:：]\s*{_value('b')}\s*\]"
_BARE_LINE = rf"^[ \t]*{_NHAC}[ \t]*[:：][ \t]*{_value('l')}[ \t]*$"
# Model nhỏ phát sinh tag tiếng Anh [MUSIC:...] (thật từ test 2026-11-15) — cùng gia đình
# thẻ điều khiển, xoá toàn bộ dòng chứa nó (nội dung sau thẻ là echo danh sách).
_MUSIC_EN_LINE = r"^[ \t]*\[[ \t]*m[u]s[i]c[ \t]*[:：].*$"

_TAG_RE = re.compile(f"{_BRACKETED}|{_BARE_LINE}|{_MUSIC_EN_LINE}", re.IGNORECASE | re.MULTILINE)


_CONTEXT_LINE_PREFIXES = ("[boi canh cuoc tro chuyen", "boi canh cuoc tro chuyen")

# Dòng facts của backend (memory.py) là regex-được 100% — filter theo NỘI DUNG chứ không
# neo duy nhất vào header "[BỐI CẢNH" (production: model echo facts bỏ header → leak).
_FACT_LINE_PREFIXES = (
    "tin nhan sap toi la luot",       # "Tin nhắn sắp tới là lượt thứ..."
    "cam xuc cac luot gan day",       # "Cảm xúc các lượt gần đây: ..."
    "luot gan nhat co goi y nhac",    # "Lượt gần nhất có gợi ý nhạc: ..."
    "nhac da goi y",                  # "Nhạc đã gợi ý: ..."
    "chua goi y nhac lan nao",
)


def _fold(text: str) -> str:
    """Bỏ dấu tiếng Việt và viết thường để so khớp tiền tố."""
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _echoes_internal(text: str) -> bool:
    """Mô hình chép lại dòng nội bộ của backend (ghi chú bối cảnh hoặc tiêu đề thẻ nhạc).

    Cho phép chip-into hợp lệ "Bài sẽ gợi ý kèm câu trả lời: <tên bài>" (PR #15 — câu model
    ĐƯỢC nói khi backend đã chọn bài): chỉ xoá khi (a) dòng mở ngoặc `[...]` mang tiêu đề
    note (dạng bể/méo), hoặc (b) có cụm "se goi" + "kem cau" nhưng KHÔNG phải prefix chuẩn
    hai chấm.
    """
    folded = _fold(text.strip())
    if folded.startswith(_CONTEXT_LINE_PREFIXES + _FACT_LINE_PREFIXES):
        return True
    legit_intro = folded.startswith("bai se goi y kem cau tra loi:")
    if folded.startswith("[") and "se goi" in folded:
        return True
    return not legit_intro and ("se goi" in folded and "kem cau" in folded)


def _drop_echo_lines(text: str) -> tuple[str, bool]:
    lines = text.split("\n")
    kept = [ln for ln in lines if not _echoes_internal(ln)]
    return "\n".join(kept), len(kept) != len(lines)


def _drop_context_lines(text: str) -> tuple[str, bool]:
    """Xoá dòng mô hình chép lại nhãn ghi chú bối cảnh (`[BỐI CẢNH CUỘC TRÒ CHUYỆN] ...`)."""
    kept = [ln for ln in text.split("\n")
            if not _fold(ln.strip()).startswith(_CONTEXT_LINE_PREFIXES)]
    return "\n".join(kept), len(kept) != len(text.split("\n"))


def split_music_tag(text: str) -> tuple[str, bool | None]:
    """Trả (câu trả lời đã xoá mọi thẻ, quyết định nhạc).

    Quyết định: True (CO), False (KHONG), None (không có thẻ). Khi có nhiều thẻ
    mâu thuẫn thì thẻ xuất hiện đầu tiên quyết định. Dòng chép lại nhãn ghi chú bối
    cảnh cũng bị xoá.
    """
    text = unicodedata.normalize("NFC", text or "")
    decision: bool | None = None
    removed = False

    def _drop(match: re.Match) -> str:
        nonlocal decision, removed
        removed = True
        if decision is None:
            value = match.group("b") or match.group("l")
            decision = None if value is None else value.lower().startswith("c")
        return ""

    cleaned = _TAG_RE.sub(_drop, text)
    cleaned, dropped_context = _drop_context_lines(cleaned)
    cleaned, dropped_echo = _drop_echo_lines(cleaned)
    if removed or dropped_context or dropped_echo:
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), decision
