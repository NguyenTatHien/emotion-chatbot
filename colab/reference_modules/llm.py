"""BẢN THAM KHẢO để test nhanh trên Colab — không phải bản nộp của Người 3.

Notebook `colab/quick_test.ipynb` chép file này vào `backend/modules/llm.py` của máy Colab.
Mô hình: Qwen/Qwen3-4B (đổi bằng LLM_MODEL_ID, ví dụ Qwen/Qwen3-1.7B nếu thiếu VRAM).
- fp16 trên T4 (T4 không hỗ trợ bf16), tắt suy luận bằng enable_thinking=False.
- Tham số sinh theo khuyến nghị của Qwen3 cho chế độ không suy luận:
  temperature 0.7, top_p 0.8, top_k 20.
Prompt viết theo cùng tinh thần với bản dự phòng Gemini (app/gemini.py) để hai nguồn trả lời
có giọng giống nhau. Thư viện nặng chỉ import trong thân hàm.
"""

import os
import re

MODEL_ID = os.environ.get("LLM_MODEL_ID", "Qwen/Qwen3-4B")
MAX_NEW_TOKENS = int(os.environ.get("LLM_MAX_NEW_TOKENS", "220"))
MAX_HISTORY_MESSAGES = 12  # 6 lượt

SYSTEM_PROMPT = (
    "Bạn là một người bạn đồng hành biết lắng nghe, trò chuyện bằng tiếng Việt. "
    "Hãy trả lời đồng cảm, ấm áp và ngắn gọn (2–4 câu), phản ánh lại cảm xúc của người dùng "
    "rồi kết thúc bằng một câu hỏi mở để họ chia sẻ thêm. "
    "Không chẩn đoán bệnh hay rối loạn tâm lý, không kê đơn, không đưa ra lời khuyên y tế. "
    "Không nói rằng bạn là con người. Chỉ trả lời bằng tiếng Việt."
)

_EMOTION_VI = {
    "Anger": "tức giận",
    "Disgust": "khó chịu",
    "Enjoyment": "vui vẻ",
    "Fear": "lo sợ",
    "Other": "bình thường",
    "Sadness": "buồn",
    "Surprise": "ngạc nhiên",
}
_AROUSAL_VI = {"low": "thấp", "medium": "trung bình", "high": "cao"}
_GOAL_VI = {
    "xoa_diu": "muốn được xoa dịu",
    "nang_mood": "muốn nâng tinh thần",
    "tap_trung": "muốn tập trung",
    "giai_toa": "muốn giải toả",
}
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

_state: dict = {}


def _load() -> dict:
    """Nạp Qwen một lần (Qwen3-4B fp16 khoảng 8 GB VRAM)."""
    if "model" not in _state:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        cuda = torch.cuda.is_available()
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch.float16 if cuda else torch.float32,
            device_map="cuda" if cuda else None,
        )
        model.eval()
        _state.update(torch=torch, tokenizer=tokenizer, model=model)
    return _state


def build_messages(
    text: str, emotion: dict, arousal: str | None, history: list[dict], goal: str | None
) -> list[dict]:
    label = (emotion or {}).get("label", "Other")
    notes = [f"cảm xúc nhận diện được: {_EMOTION_VI.get(label, label)}"]
    if arousal in _AROUSAL_VI:
        notes.append(f"mức kích động trong giọng nói: {_AROUSAL_VI[arousal]}")
    if goal in _GOAL_VI:
        notes.append(f"người dùng {_GOAL_VI[goal]} bằng âm nhạc")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-MAX_HISTORY_MESSAGES:]:
        role = "assistant" if m.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": str(m.get("content", ""))})
    messages.append({"role": "user", "content": f"[{'; '.join(notes)}]\n{text}"})
    return messages


def generate_reply(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None = None,
) -> str:
    """Sinh 2–4 câu đồng cảm, kết thúc bằng câu hỏi mở."""
    s = _load()
    tokenizer, model, torch = s["tokenizer"], s["model"], s["torch"]
    prompt = tokenizer.apply_chat_template(
        build_messages(text, emotion, arousal, history, goal),
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = output[0][inputs["input_ids"].shape[1] :]
    reply = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return _THINK_RE.sub("", reply).strip()
