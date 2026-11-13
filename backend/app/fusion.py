"""Late fusion theo luật: giọng nói (arousal) điều chỉnh xác suất cảm xúc từ chữ.

Mô hình valence-arousal của Russell: chữ quyết định valence, giọng điều chỉnh theo arousal.
Đây là luật theo lý thuyết, hệ số alpha chưa được đo độ chính xác trên dữ liệu thật.
"""

from app.constants import LABELS

HIGH_AROUSAL = frozenset({"Anger", "Fear", "Surprise", "Enjoyment"})
LOW_AROUSAL = frozenset({"Sadness", "Other"})
# Disgust không thuộc nhóm nào nên giữ nguyên trọng số 1.


def _weight(label: str, arousal: str, alpha: float) -> float:
    if label in HIGH_AROUSAL:
        return 1 + alpha if arousal == "high" else 1 - alpha
    if label in LOW_AROUSAL:
        return 1 + alpha if arousal == "low" else 1 - alpha
    return 1.0


def fuse(probs: dict[str, float], arousal: str, alpha: float) -> dict[str, float]:
    """Nhân xác suất từ chữ với trọng số theo arousal rồi chuẩn hoá để tổng bằng 1."""
    if arousal not in ("low", "high"):
        return dict(probs)
    weighted = {k: probs[k] * _weight(k, arousal, alpha) for k in LABELS}
    total = sum(weighted.values())
    if total <= 0:
        return dict(probs)
    return {k: v / total for k, v in weighted.items()}


def apply_fusion(
    emotion_dict: dict, arousal: str | None, alpha: float, from_module: bool
) -> tuple[dict, bool]:
    """Áp dụng fusion nếu đủ điều kiện; trả (emotion_dict, đã_áp_dụng).

    Điều kiện: arousal là low/high, cảm xúc đến từ module thật (không phải dự phòng), alpha > 0.
    Khi áp dụng, `label`/`probs` là kết quả đã kết hợp, còn `label_text`/`probs_text` giữ kết quả
    chỉ từ chữ. Hoà xác suất thì giữ nhãn từ chữ.
    """
    if arousal not in ("low", "high") or not from_module or alpha <= 0:
        return emotion_dict, False
    label_text = emotion_dict["label"]
    probs_text = emotion_dict["probs"]
    probs = fuse(probs_text, arousal, alpha)
    top = max(probs.values())
    # Hoà (sai số số thực) thì giữ nhãn từ chữ; ngược lại lấy argmax.
    if probs[label_text] >= top - 1e-9:
        label = label_text
    else:
        label = max(LABELS, key=lambda k: probs[k])
    return (
        {
            "label": label,
            "probs": probs,
            "label_text": label_text,
            "probs_text": dict(probs_text),
        },
        True,
    )
