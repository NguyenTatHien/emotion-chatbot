"""Bảng giọng điệu: từ cảm xúc (đã qua fusion) và mức kích động chọn một hướng dẫn ngắn.

Backend là nơi duy nhất quyết định giọng điệu; LLM (Qwen hay Gemini) chỉ nhận dòng
`Giọng điệu nên dùng: <text>` trong ghi chú bối cảnh. Nguyên tắc chung: khớp cảm xúc trước,
dẫn dắt sau.
"""

UNCERTAIN_THRESHOLD = 0.5

TONES: dict[str, str] = {
    "uncertain": (
        "Trung tính, phản ánh nhẹ nhàng điều người dùng nói, hỏi thêm để hiểu rõ, "
        "không đoán cảm xúc."
    ),
    "sad_high": "Trấn an trước, giữ nhịp bình tĩnh, câu ngắn, không hỏi dồn.",
    "sad": "Chậm, dịu, ghi nhận cảm xúc trước, chưa vội khuyên.",
    "fear": "Trấn an, giúp người dùng chia nhỏ điều đang lo cho cụ thể.",
    "anger": (
        "Ghi nhận cơn giận là có lý, không phán xét, không bảo người dùng bình tĩnh, không đùa."
    ),
    "disgust": "Ghi nhận sự khó chịu, tò mò về nguyên nhân, không bênh phía bên kia.",
    "joy": "Chung vui, nhiều năng lượng hơn, hỏi thêm về điều vui.",
    "surprise": "Tò mò cùng người dùng, hỏi chuyện gì vừa xảy ra.",
    "neutral": "Tự nhiên, thân thiện, ngắn gọn.",
}

_BY_LABEL = {
    "Fear": "fear",
    "Anger": "anger",
    "Disgust": "disgust",
    "Enjoyment": "joy",
    "Surprise": "surprise",
}


def _max_prob(emotion: dict) -> float:
    probs = emotion.get("probs") or {}
    try:
        return max((float(p) for p in probs.values()), default=0.0)
    except (TypeError, ValueError):
        return 0.0


def choose_tone(emotion: dict, arousal: str | None) -> dict:
    """Trả `{"key", "text"}` theo bảng giọng điệu, xét theo thứ tự từ trên xuống."""
    label = emotion.get("label")
    if _max_prob(emotion) < UNCERTAIN_THRESHOLD:
        key = "uncertain"
    elif label == "Sadness":
        key = "sad_high" if arousal == "high" else "sad"
    else:
        key = _BY_LABEL.get(str(label), "neutral")
    return {"key": key, "text": TONES[key]}
