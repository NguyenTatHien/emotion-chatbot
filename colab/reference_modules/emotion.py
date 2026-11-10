"""BẢN THAM KHẢO để test nhanh trên Colab — không phải bản nộp của Người 1.

Notebook `colab/quick_test.ipynb` chép file này vào `backend/modules/emotion.py` của máy Colab
(không đụng tới repo). Người 1 có thể dùng làm điểm xuất phát rồi thay bằng bản chính thức.

Mô hình: BaoNhan/cafebert-UITVSMEC (XLM-R, đã fine-tune trên UIT-VSMEC, nhận câu thô không cần
tách từ). id2label của checkpoint đúng thứ tự LABELS bên dưới.
Thư viện nặng chỉ import trong thân hàm (contract test kiểm tra điều này).
"""

import os

LABELS = ["Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise"]

MODEL_ID = os.environ.get("EMOTION_MODEL_ID", "BaoNhan/cafebert-UITVSMEC")
MAX_TOKENS = 256

_state: dict = {}


def _load() -> dict:
    """Nạp tokenizer + model một lần (lần đầu tải khoảng 2,2 GB)."""
    if "model" not in _state:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, dtype=dtype)
        model.to(device).eval()
        _state.update(torch=torch, tokenizer=tokenizer, model=model, device=device)
    return _state


def predict_emotion(text: str) -> dict:
    """-> {"label": str trong LABELS, "probs": {label: float}} (tổng probs = 1)."""
    text = (text or "").strip()
    if not text:
        probs = {label: (1.0 if label == "Other" else 0.0) for label in LABELS}
        return {"label": "Other", "probs": probs}

    s = _load()
    torch = s["torch"]
    enc = s["tokenizer"](text, truncation=True, max_length=MAX_TOKENS, return_tensors="pt")
    enc = {k: v.to(s["device"]) for k, v in enc.items()}
    with torch.inference_mode():
        logits = s["model"](**enc).logits[0].float()
    values = torch.softmax(logits, dim=-1).tolist()

    id2label = s["model"].config.id2label
    raw = {str(id2label[i]): float(p) for i, p in enumerate(values)}
    total = sum(raw.get(label, 0.0) for label in LABELS) or 1.0
    probs = {label: raw.get(label, 0.0) / total for label in LABELS}
    label = max(probs, key=probs.get)
    return {"label": label, "probs": probs}
