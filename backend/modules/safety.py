"""Hợp đồng module an toàn — Người 3 phụ trách.

Ghi chú: bản triển khai này do Hiển viết thay Người 3 (theo OpenSpec `add-safety-module`)
và cần Người 3 review trước khi coi là bản chính thức.

Hàm này chạy TRƯỚC mọi bước khác. KHÔNG import thư viện nặng ở đầu file.

Cách làm: bộ lọc theo luật, thuần Python (regex), không mô hình học máy, không gọi mạng.
  1. Chuẩn hoá: NFC, chữ thường, bỏ dấu câu, gộp khoảng trắng, mở rộng vài cách viết tắt
     ("ko", "k", "hok"... thành "không"). Tạo thêm bản bỏ dấu để bắt câu gõ không dấu.
  2. Gỡ các đoạn thành ngữ cường điệu ("nóng muốn chết") và đoạn phủ định rõ ràng
     ("không bao giờ có ý định tự tử") ra khỏi câu.
  3. Tìm cụm nguy hiểm trong phần còn lại; còn cụm nào thì `risk=True`.
Bước 2 chỉ gỡ đúng đoạn đó nên tín hiệu nguy hiểm khác trong cùng câu vẫn được bắt
("mệt muốn chết, chắc tự tử cho xong" vẫn là rủi ro). Khi phân vân thì nghiêng về rủi ro.
"""

import re
import unicodedata
from functools import lru_cache

_PRONOUN = r"(?:mình|tôi|em|tui|con|tao|tớ|anh|chị)"
_ME = r"(?:mình|tôi|em|tui|con)"

# Cụm đủ rõ nghĩa để so khớp trên chữ đã bỏ dấu (viết có dấu cho dễ đọc,
# bản bỏ dấu được suy ra bằng strip_accents).
_RISK_SAFE = [
    # Ý định tự tử, tự làm hại
    r"tự sát",
    r"tự làm hại",
    r"tự hại(?: bản thân| mình)?",
    r"tự gây thương tích",
    r"tự làm đau(?: bản thân| mình)?",
    r"tự huỷ hoại|tự hủy hoại",
    r"tự hành hạ(?: bản thân| mình)?",
    r"làm hại bản thân",
    r"làm đau bản thân",
    r"kết liễu",
    r"kết thúc (?:cuộc đời|đời mình|đời tôi|cuộc sống|mạng sống|sự sống|cái đời|tất cả)",
    rf"(?:nên|sẽ|định|muốn|phải|đành|để|{_ME}(?: sẽ| nên| định| muốn| phải)?) kết thúc "
    r"(?:hết )?(?:mọi thứ|mọi chuyện)(?! với| giữa| mối)",
    r"muốn chết",
    r"muốn được chết",
    r"mong (?:được )?chết",
    r"chết (?:đi )?cho rồi",
    r"chết quách",
    r"(?:nên|phải) chết đi",
    rf"(?:ước gì|giá như|ước|ước chi|phải chi|mong) (?:{_PRONOUN} )?(?:chết|biến mất"
    r"|không tồn tại|không được sinh ra)",
    # Mong chưa từng được sinh ra
    r"chưa (?:từng|bao giờ) (?:được )?(?:sinh ra|tồn tại|có mặt (?:trên đời|trên thế giới))",
    rf"(?:{_ME} )?(?:không nên|đáng lẽ không nên|lẽ ra không nên|không đáng) "
    r"(?:được )?(?:sinh ra|tồn tại|sống)",
    r"sinh ra (?:để )?làm gì",
    r"tìm cách chết",
    r"cách (?:nào )?chết (?:không đau|nhẹ nhàng|nhanh)",
    r"chết (?:không|ít) đau",
    # Kế hoạch, phương tiện
    r"uống (?:hết |cả )?(?:vỉ |lọ |chai )?thuốc (?:ngủ )?(?:cho xong|để chết|quá liều|hết luôn)",
    r"uống thuốc (?:độc|trừ sâu|chuột)",
    r"uống quá liều",
    r"uống hết (?:vỉ|lọ|chai) thuốc",
    r"nhảy (?:cầu|lầu|sông|xuống (?:sông|cầu|lầu|biển)|từ (?:tầng|sân thượng|trên cao))",
    r"(?:cắt|cứa|rạch) (?:cổ )?tay(?! áo)",
    r"cứa (?:vào )?(?:cổ tay|cổ)",
    r"(?:rạch|cắt) (?:vào )?(?:cổ tay|mạch)",
    r"treo cổ",
    r"thắt cổ",
    r"thư (?:tuyệt mệnh|từ biệt|vĩnh biệt|trăn trối)|lời (?:tuyệt mệnh|trăn trối)",
    r"(?:viết|để lại|gửi|soạn|chuẩn bị)(?: sẵn| xong)?(?: một)?(?: lá| bức)? "
    r"(?:thư|lời) (?:từ biệt|vĩnh biệt|tuyệt mệnh|trăn trối|cuối cùng)",
    r"(?:viết|để lại|làm|chuẩn bị)(?: sẵn| xong)? di chúc",
    r"(?:lo|dặn dò|sắp xếp) hậu sự",
    r"vĩnh biệt (?:mọi người|cả nhà|gia đình|bố mẹ|ba mẹ|thế giới|cuộc đời)",
    r"lời nhắn cuối cùng",
    # Gom, giấu phương tiện
    r"(?:tích|gom|trữ|dành dụm|để dành|giấu|cất)(?: được| sẵn)?(?: cả| hết| đủ| nhiều| nguyên)?"
    r"(?: từng| một| mấy| \d+)?(?: lọ| vỉ| chai| viên| hộp| cuộn| con| cái| chiếc| sợi)? "
    r"(?:thuốc ngủ|thuốc an thần|thuốc|dao lam|lưỡi dao|dao|dây thừng|dây|than)(?! ho| cảm| bổ)",
    r"chuẩn bị sẵn (?:thuốc|dao|dây|dây thừng|than)",
    r"(?:mua|kiếm|có) (?:sẵn )?(?:thuốc độc|lưỡi dao lam|dao lam)",
    # Mong biến mất, tuyệt vọng
    r"(?:không|chẳng|chả) (?:còn )?muốn sống(?! (?:chung|ở|tại|cùng|với|trong|như|theo|kiểu"
    r"|một|gần|xa|bên|trên|dưới))",
    r"hết muốn sống",
    r"chán sống",
    r"không muốn (?:tiếp tục sống|còn sống|tồn tại|có mặt trên đời)",
    r"không muốn (?:tỉnh|thức) dậy(?: nữa)?",
    r"không muốn mở mắt(?: ra)? nữa",
    r"mong (?:không|đừng) (?:tỉnh|thức) dậy",
    # Muốn ngủ vĩnh viễn, không thức dậy
    r"ngủ (?:một giấc |luôn |mãi |và )*(?:mãi mãi|ngàn thu|vĩnh viễn)",
    r"ngủ (?:một giấc |luôn |mãi |và )*(?:không|chẳng) (?:bao giờ )?(?:tỉnh|dậy|thức)",
    r"giấc ngủ (?:ngàn thu|vĩnh hằng|không bao giờ tỉnh)",
    r"(?:nhắm mắt|ngủ) (?:rồi )?(?:không|chẳng) (?:bao giờ )?(?:mở|tỉnh|dậy)",
    r"sống làm gì nữa",
    r"sống để làm (?:gì|cái gì)",
    r"còn sống làm gì|sống thêm làm gì",
    r"(?:không|chẳng) còn (?:lý do|lí do|động lực|hy vọng|hi vọng|mục đích|ý nghĩa|gì)"
    r"(?: gì)?(?: nào)? (?:để )?(?:tiếp tục )?sống",
    r"(?:không|chẳng|chả) (?:còn )?thiết (?:tha )?(?:gì )?(?:sống|cuộc sống|cuộc đời|đời)",
    r"(?:không|chẳng) (?:thể|nổi|muốn) (?:tiếp tục )?sống (?:tiếp|nữa)",
    r"sống tiếp (?:làm gì|để làm gì)",
    r"(?:không|chẳng) có (?:lý do|lí do) (?:gì )?để sống",
    r"sống (?:cũng )?(?:vô nghĩa|chẳng có ý nghĩa gì|không có ý nghĩa gì)",
    r"(?:không|chẳng) ai cần (?:đến )?(?:mình|tôi|em|tui|con)",
    r"(?:chỉ )?là (?:một )?gánh nặng (?:của|cho|với|đối với) (?:mọi người|gia đình"
    r"|bố mẹ|ba mẹ|cả nhà|người khác)",
    rf"{_ME} (?:chỉ )?là gánh nặng",
    rf"(?:{_ME} )?(?:muốn|mong|ước(?: gì)?) (?:được )?biến mất",
    rf"(?<!của ){_ME} biến mất",
    r"biến mất (?:khỏi|vĩnh viễn|mãi mãi|luôn đi)",
    r"biến khỏi (?:thế giới|cuộc đời|thế gian)",
    r"ra đi (?:mãi mãi|vĩnh viễn|thanh thản)",
    r"(?:rời|rời bỏ|rời xa|từ biệt) (?:khỏi )?(?:thế giới|cuộc đời|thế gian|đời) này",
    r"từ biệt mọi người",
    r"không (?:còn )?tồn tại (?:trên đời|trên thế giới)",
    # Câu nói vòng kiểu "không có mình thì mọi người nhẹ nhõm hơn"
    rf"(?:biến mất|không có {_ME}|không còn {_ME}|{_ME} (?:đi|chết)) (?:thì |đi thì )?"
    r"(?:mọi người|cả nhà|gia đình|bố mẹ|ba mẹ|mẹ|ai cũng)(?: sẽ| cũng)? "
    r"(?:nhẹ nhõm|tốt hơn|hạnh phúc hơn|đỡ khổ|đỡ vất vả|thoải mái hơn)",
    r"(?:mọi người|cả nhà|gia đình|bố mẹ|ba mẹ|mẹ)(?: sẽ| cũng)? "
    rf"(?:nhẹ nhõm|tốt hơn|hạnh phúc hơn|đỡ khổ|đỡ vất vả)(?: hơn)? (?:nếu|khi) "
    rf"(?:không có|không còn) {_ME}",
]

# Cụm chỉ khớp trên chữ CÓ DẤU, vì bản bỏ dấu trùng với từ thường ("từ từ", "tư vấn").
_RISK_ACCENTED = [
    r"tự tử",
    r"tự vẫn",
    r"tu tử",
]

# Người dùng gõ không dấu: "tu tu" dễ lẫn với "từ từ" nên chỉ nhận khi có ngữ cảnh rõ.
_AMBIGUOUS_CONTEXT = [
    "muốn",
    "định",
    "nghĩ tới",
    "nghĩ đến",
    "nghĩ về",
    "ý định",
    "kế hoạch",
    "có ý",
    "chuyện",
    "vụ",
    "thử",
    "tính",
]

# Thành ngữ cường điệu: "<tính từ> muốn chết".
_IDIOM_ADJ = (
    r"nóng|đói|mệt|mệt mỏi|cười|buồn cười|mắc cười|sợ|lạnh|buồn ngủ|ngại|ngượng|xấu hổ|khát"
    r"|nắng|ngứa|thèm|no|nhột|lười|bực mình|bực|tức|khó|khó chịu|phiền|ồn|chật|đông|nhiều"
    r"|dài|nặng|ngán|nhàm|ngon|đẹp|hài|dễ thương|đáng yêu|hồi hộp|run|thích|sướng"
)
_IDIOM = (
    rf"(?:{_IDIOM_ADJ})(?: quá| lắm| thật| ghê| rồi| vãi)?(?: đến| tới)? "
    r"(?:muốn chết|chết cho rồi|chết đi cho rồi)(?: cười| mê| thèm| khiếp)?"
    r"|muốn chết (?:cười|vì (?:ngại|xấu hổ|ngượng|cười|đói|nóng|lạnh|buồn ngủ|sợ|mệt))"
)

# Phủ định rõ ràng: "không (bao giờ) (có ý định | muốn | nghĩ đến) tự tử / chết ...".
_NEG_OBJECT = (
    r"chết|tự tử|tu tu|tự vẫn|tự sát|biến mất|tự làm hại(?: bản thân)?|làm hại bản thân"
    r"|kết liễu(?: đời mình)?|nhảy cầu|nhảy lầu|cắt tay"
)
_NEGATION = (
    r"(?:không|chưa|chẳng|đâu có|đâu)(?: bao giờ| hề| từng)*(?: có ý định| có ý nghĩ| có| muốn"
    r"| định| nghĩ (?:tới|đến|về))*(?: bao giờ)?(?: chuyện| việc)? (?:" + _NEG_OBJECT + r")"
)

# Ngữ cảnh kể chuyện/đưa tin về người khác (truyện, phim, nhân vật, bài báo...). Khi câu rõ ràng
# chỉ kể lại như vậy và KHÔNG có dấu hiệu ý định của chính người nói, các từ "tường thuật"
# (tự tử, nhảy cầu, cắt tay...) không tính là rủi ro. Còn nghi ngờ thì vẫn nghiêng về rủi ro.
_MEDIA = (
    r"truyện|tiểu thuyết|bộ phim|phim|nhân vật|bài báo|tin tức|bản tin|cuốn sách|quyển sách"
    r"|sách|kịch|vở kịch|series|anime|manga|webtoon|bài thơ|bài hát|vụ án|tài liệu|phóng sự"
)
_REPORTING = [
    r"tự tử",
    r"tự vẫn",
    r"tự sát",
    r"kết liễu(?: đời mình| cuộc đời)?",
    r"nhảy (?:cầu|lầu|sông)",
    r"treo cổ",
    r"thắt cổ",
    r"(?:cắt|cứa|rạch) (?:cổ )?tay",
    r"tự làm hại(?: bản thân)?",
    r"tự hại(?: bản thân)?",
]
# Dấu hiệu ý định của chính người nói: "mình cũng muốn", "chỉ muốn", "giống mình"...
_FIRST_PERSON_INTENT = (
    rf"{_PRONOUN}(?: cũng| chỉ| đang| sẽ| đã| hay| luôn| thật sự)* (?:muốn|định|nghĩ (?:tới|đến|về)"
    r"|giống|làm theo|cũng vậy|cũng thế)"
    r"|(?:chỉ|cũng|lại|rất|thật sự) (?:muốn|định)|giống (?:mình|tôi|em|tui)"
    r"|(?:đồng cảm|làm theo|bắt chước|y như|như vậy)|thấy (?:mình|tôi|em|tui)"
)

# Viết tắt phổ biến trong tin nhắn.
_ABBREVIATIONS = {"ko": "không", "k": "không", "khg": "không", "hok": "không", "kh": "không"}


def _bounded(parts: list[str] | str) -> re.Pattern:
    body = parts if isinstance(parts, str) else "|".join(parts)
    return re.compile(r"(?<!\w)(?:" + body + r")(?!\w)")


@lru_cache(maxsize=1)
def _rules() -> dict:
    """Biên dịch luật một lần. `app.fallbacks` chỉ import ở đây (D3) để import module vẫn nhẹ."""
    from app.fallbacks import strip_accents

    context = "|".join(_AMBIGUOUS_CONTEXT + [strip_accents(c) for c in _AMBIGUOUS_CONTEXT])
    return {
        "strip": strip_accents,
        "media": _bounded(strip_accents(_MEDIA)),
        "intent": _bounded(strip_accents(_FIRST_PERSON_INTENT)),
        "report_accented": _bounded(_REPORTING),
        "report_plain": _bounded([strip_accents(p) for p in _REPORTING]),
        "idiom": _bounded(strip_accents(_IDIOM)),
        "neg_accented": _bounded([_NEGATION, strip_accents(_NEGATION)]),
        "neg_plain": _bounded(strip_accents(_NEGATION)),
        "risk_plain": _bounded([strip_accents(p) for p in _RISK_SAFE]),
        "risk_accented": _bounded(
            _RISK_ACCENTED + [rf"(?:{context}) tu tu", r"tu tu (?:cho xong|luôn|thật|luon|that)"]
        ),
    }


def _normalize(text: str) -> str:
    """NFC, chữ thường, bỏ dấu câu, gộp khoảng trắng, mở rộng viết tắt."""
    lowered = unicodedata.normalize("NFC", text or "").lower()
    lowered = re.sub(r"[\W_]+", " ", lowered).strip()
    return " ".join(_ABBREVIATIONS.get(w, w) for w in lowered.split(" "))


def _has_risk(text: str) -> bool:
    lowered = _normalize(text)
    if not lowered:
        return False
    rules = _rules()

    # Câu chỉ kể lại chuyện của người khác: gỡ các từ tường thuật trước khi dò.
    plain_view = rules["strip"](lowered)
    narrative = bool(rules["media"].search(plain_view)) and not rules["intent"].search(plain_view)
    if narrative:
        lowered = rules["report_accented"].sub(" ", lowered)

    # Chữ giữ nguyên dấu: bắt "tự tử", "tự vẫn" và "tu tu" có ngữ cảnh (gõ không dấu).
    if rules["risk_accented"].search(rules["neg_accented"].sub(" ", lowered)):
        return True

    # Chữ bỏ dấu: bắt câu gõ không dấu và mọi cụm còn lại, sau khi gỡ thành ngữ và phủ định.
    plain = plain_view
    if narrative:
        plain = rules["report_plain"].sub(" ", plain)
    plain = rules["neg_plain"].sub(" ", rules["idiom"].sub(" ", plain))
    return bool(rules["risk_plain"].search(plain))


def check_safety(text: str) -> dict:
    """Phát hiện dấu hiệu tự làm hại.

    Đầu vào: `text` — văn bản người dùng.
    Đầu ra: {"risk": bool, "message": str | None}
      - Khi `risk=True`, `message` là thông điệp an toàn hiển thị cho người dùng.
    """
    if not _has_risk(text):
        return {"risk": False, "message": None}
    # Import trong thân hàm để import module vẫn nhẹ (design D3).
    from app.fallbacks import safety_message

    return {"risk": True, "message": safety_message()}
