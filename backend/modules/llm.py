"""Hợp đồng module sinh câu trả lời — Người 3 phụ trách.

KHÔNG import torch / transformers / SDK nặng ở đầu file; import bên trong thân hàm.
"""


def generate_reply(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None = None,
) -> str:
    """Sinh câu trả lời đồng cảm bằng tiếng Việt.

    Đầu vào:
      - text: lời người dùng
      - emotion: {"label": str, "probs": dict[str, float]}
      - arousal: "low" | "medium" | "high" | None
      - history: [{"role": "user" | "assistant", "content": str}, ...] (cũ -> mới)
      - goal: "xoa_diu" | "nang_mood" | "tap_trung" | "giai_toa" | None
    Đầu ra: chuỗi câu trả lời, nên kết thúc bằng một câu hỏi mở.
    """
    raise NotImplementedError("Người 3 phụ trách: generate_reply (Qwen3 / Gemini)")
