"""Hợp đồng module cảm xúc — Người 1 phụ trách.

Thay thân hàm `predict_emotion` bằng mô hình thật (CafeBERT). KHÔNG import torch /
transformers ở đầu file: hãy import bên trong hàm (hoặc trong hàm tải mô hình có cache).
"""

LABELS = ["Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise"]


def predict_emotion(text: str) -> dict:
    """Phân loại cảm xúc của một đoạn văn bản tiếng Việt.

    Đầu vào: `text` — chuỗi bất kỳ (có thể rỗng, có emoji).
    Đầu ra: {"label": str, "probs": dict[str, float]}
      - `label` thuộc LABELS
      - `probs` có đủ 7 khóa của LABELS, tổng xấp xỉ 1
    """
    raise NotImplementedError("Người 1 phụ trách: predict_emotion (CafeBERT, 7 nhãn)")
