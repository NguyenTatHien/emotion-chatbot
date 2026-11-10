"""Module cảm xúc — CafeBERT (BaoNhan/cafebert-UITVSMEC), 7 nhãn.

Thiết kế:
- Import torch/transformers BÊN TRONG hàm (lazy): giữ cho lần import module
  luôn nhẹ — `tests/contract/test_import_is_light.py` chạy subprocess và assert
  không có torch/transformers/librosa trong sys.modules sau khi import.
- Model + tokenizer được cache ở mức module sau lần tải đầu tiên
  (`_STATE`) để các request sau không phải load lại.
- Đầu ra luôn có đủ 7 khóa của LABELS (theo đúng thứ tự module), tổng
  probs xấp xỉ 1 (softmax), label ∈ LABELS.

Nguồn model: huggingface `BaoNhan/cafebert-UITVSMEC` (UIT-VSMEC, 7 nhãn).
Nhãn trong LABELS xếp theo alphabet và trùng bộ nhãn UIT-VSMEC gốc; ta
kiểm tra `model.config.id2label` khi tải: nếu tên nhãn khớp thì dùng mapping
đúng, không thì fallback theo vị trí index (giữ hành vi an toàn khi
checkpoint không có id2label chuẩn).
"""

LABELS = ["Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise"]

# Cache 1 lần: {"tokenizer": ..., "model": ..., "index_to_label": [...]}
_STATE: dict | None = None

_MODEL_NAME = "BaoNhan/cafebert-UITVSMEC"


def _normalize_label(raw: str) -> str:
    """Chuẩn hoá tên nhãn từ id2label: 'LABEL_3' / ' enjoyment' -> 'Enjoyment'."""
    return raw.strip().split("_")[-1].strip().title()


def _load_model():
    """Tải model + tokenizer 1 lần; trả về state có mapping index -> nhãn LABELS."""
    global _STATE
    if _STATE is not None:
        return _STATE

    # Lazy import bắt buộc: torch/transformers chỉ được nạp khi gọi hàm.
    import warnings

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    # use_fast=False: repo CafeBERT chỉ có sentencepiece.bpe.model, thiếu
    # tokenizer.json — fast tokenizer của transformers 5.x chuyển sai qua
    # TikToken extractor. Slow tokenizer (sentencepiece) đọc đúng chuẩn.
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, use_fast=False)
    torch.set_num_threads(max(1, (torch.get_num_threads() or 1)))
    if torch.cuda.is_available():
        device = "cuda"
    elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        device = "mps"  # Apple Silicon local; falls back nếu model không chạy được
    else:
        device = "cpu"

    model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)

    model.eval()
    model.to(device)

    # Build mapping index -> nhãn chuẩn LABELS. id2label có thể lưu key
    # int hoặc str ("0".."6") tùy cách checkpoint được serialize — tra cả hai.
    id2label = getattr(model.config, "id2label", None) or {}
    normalized = []
    unmatched = False
    for idx in range(int(getattr(model.config, "num_labels", len(LABELS)))):
        raw = str(id2label.get(idx, id2label.get(str(idx), "")))
        name = _normalize_label(raw) if raw else ""
        if name in LABELS:
            normalized.append(name)
        else:
            unmatched = True
            normalized.append(None)  # tạm để biết vị trí nào không map được

    if unmatched or len(normalized) != len(LABELS):
        # Fallback an toàn: checkpoint không có/id2label lạ — coi nhãn xếp
        # theo cùng thứ tự UIT-VSMEC gốc (alphabet, giống LABELS).
        warnings.warn(
            "CafeBERT id2label không khớp LABELS chuẩn; dùng mapping theo vị trí index.",
            stacklevel=2,
        )
        index_to_label = [LABELS[i % len(LABELS)] for i in range(len(normalized))]
    else:
        index_to_label = normalized

    _STATE = {
        "tokenizer": tokenizer,
        "model": model,
        "index_to_label": index_to_label,
        "device": device,
    }
    return _STATE


def predict_emotion(text: str) -> dict:
    """Phân loại cảm xúc của một đoạn văn bản tiếng Việt.

    Đầu vào: `text` — chuỗi bất kỳ (có thể rỗng, có emoji).
    Đầu ra: {"label": str, "probs": dict[str, float]}
      - `label` thuộc LABELS
      - `probs` có đủ 7 khóa của LABELS, tổng xấp xỉ 1
    """
    import torch
    import torch.nn.functional as F

    state = _load_model()
    tokenizer, model, mapping = state["tokenizer"], state["model"], state["index_to_label"]

    # Chuỗi rỗng/toàn khoảng trắng: tokenizer + phobert có thể trả tensor
    # rỗng gây IndexError — trả về phân bố đều trước, label mặc định 'Other'
    # (mô phỏng "không tin hiệu cảm xúc rõ").
    if not text or not text.strip():
        probs = {label: 1.0 / len(LABELS) for label in LABELS}
        return {"label": "Other", "probs": probs}

    # Text dài: phoBERT giới hạn 256 token — cắt lại trước khi tokenize.
    with torch.no_grad():
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        inputs = {k: v.to(state["device"]) for k, v in inputs.items()}
        logits = model(**inputs).logits[0]          # shape: (num_labels,)
        probs_tensor = F.softmax(logits, dim=-1).cpu()

    probs = {label: 0.0 for label in LABELS}
    best_idx = 0
    best_p = -1.0
    for idx, p in enumerate(probs_tensor.tolist()):
        label = mapping[idx] if idx < len(mapping) else "Other"
        probs[label] += float(p)
        if p > best_p:
            best_p, best_idx = p, idx
    # Đảm bảo tổng chuẩn sau cộng float (chống sai lệch 1e-12).
    total = sum(probs.values())
    if total > 0:
        probs = {k: v / total for k, v in probs.items()}
    top_label = mapping[best_idx] if best_idx < len(mapping) else "Other"
    if top_label not in LABELS:  # an toàn cuối cùng cho contract
        top_label = max(probs, key=probs.get)
    return {"label": top_label, "probs": probs}
