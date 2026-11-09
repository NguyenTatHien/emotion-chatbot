"""Hợp đồng module an toàn — Người 3 phụ trách.

Hàm này chạy TRƯỚC mọi bước khác. KHÔNG import thư viện nặng ở đầu file.
"""


def check_safety(text: str) -> dict:
    """Phát hiện dấu hiệu tự làm hại.

    Đầu vào: `text` — văn bản người dùng.
    Đầu ra: {"risk": bool, "message": str | None}
      - Khi `risk=True`, `message` là thông điệp an toàn hiển thị cho người dùng.
    """
    raise NotImplementedError("Người 3 phụ trách: check_safety")
