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


_BRACKETED = rf"\[\s*{_NHAC}\s*[:：]\s*{_value('b')}\s*\]"
_BARE_LINE = rf"^[ \t]*{_NHAC}[ \t]*[:：][ \t]*{_value('l')}[ \t]*$"

_TAG_RE = re.compile(f"{_BRACKETED}|{_BARE_LINE}", re.IGNORECASE | re.MULTILINE)


def split_music_tag(text: str) -> tuple[str, bool | None]:
    """Trả (câu trả lời đã xoá mọi thẻ, quyết định nhạc).

    Quyết định: True (CO), False (KHONG), None (không có thẻ). Khi có nhiều thẻ
    mâu thuẫn thì thẻ xuất hiện đầu tiên quyết định.
    """
    text = unicodedata.normalize("NFC", text or "")
    decision: bool | None = None
    removed = False

    def _drop(match: re.Match) -> str:
        nonlocal decision, removed
        removed = True
        if decision is None:
            value = match.group("b") or match.group("l")
            decision = value.lower().startswith("c")
        return ""

    cleaned = _TAG_RE.sub(_drop, text)
    if removed:
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), decision
