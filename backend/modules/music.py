"""Hợp đồng module gợi ý nhạc — Người 5 phụ trách.

KHÔNG import thư viện nặng ở đầu file; import bên trong thân hàm.
"""


def recommend(label: str, arousal: str | None, goal: str | None, k: int = 5) -> list[dict]:
    """Gợi ý bài hát theo cảm xúc, mức kích động và mục tiêu nghe nhạc.

    Đầu vào: label (1 trong 7 nhãn), arousal ("low"|"medium"|"high"|None),
             goal ("xoa_diu"|"nang_mood"|"tap_trung"|"giai_toa"|None), k (số bài tối đa).
    Đầu ra: danh sách tối đa k phần tử
      {"title": str, "artist": str, "youtube_url": str, "reason": str}
    """
    raise NotImplementedError("Người 5 phụ trách: recommend")
