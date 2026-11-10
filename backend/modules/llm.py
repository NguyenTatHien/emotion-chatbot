"""Module sinh câu trả lời — Qwen chat (Qwen2.5-3B local / Qwen3-4B trên Colab).

Thiết kế:
- Import torch/transformers BÊN TRONG hàm (lazy) — bắt buộc vì
  `tests/contract/test_import_is_light.py` assert module nạp nhẹ.
- Tên model đọc từ env `LLM_MODEL`:
  - mặc định (laptop dev): `Qwen/Qwen2.5-3B-Instruct` (~6GB, chạy MPS/CPU đủ nhanh)
  - Colab T4: set `LLM_MODEL=Qwen/Qwen3-4B-Instruct-2507` (~8GB fp16, đúng
    phương án của Thầy, còn dư VRAM cho CafeBERT + PhoWhisper trên cùng GPU)
- max_new_tokens=128 giữ độ trễ < 30s (LLM_TIMEOUT=30 của pipeline).
  Nếu quá thời hạn hoặc model lỗi, trả về câu trả lời an toàn ngắn thay vì
  raise — pipeline đã có fallback canned reply phía `app/pipeline.py`, nhưng
  contract module yêu cầu luôn trả đúng kiểu str.

Cache model + tokenizer ở mức module (`_LLM_STATE`) — load 1 lần/lifetime.
"""

_LLM_STATE: dict | None = None
_DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct"

# Giới hạn lượt lịch sử đưa vào prompt (backend cũng cắt 6 lượt, chặn lại
# ở đây phòng khi test gọi trực tiếp với history dài).
_MAX_HISTORY_TURNS = 6

_GOAL_HINTS = {
    "xoa_diu": "Lời khuyên: trấn an, nhẹ nhàng, đồng hành.",
    "nang_mood": "Lời khuyên: động viên, thêm năng lượng tích cực.",
    "tap_trung": "Lời khuyên: giúp người dùng tập trung, mạch lạc lại.",
    "giai_toa": "Lời khuyên: giúp buông, giải toả, nhìn sự việc nhẹ đi.",
}


def _get_llm():
    """Tải Qwen + tokenizer 1 lần (lazy import, chọn device cuda > mps > cpu)."""
    global _LLM_STATE
    if _LLM_STATE is not None:
        return _LLM_STATE

    import os

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_name = os.environ.get("LLM_MODEL", _DEFAULT_MODEL)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    if torch.cuda.is_available():
        device = "cuda"
        dtype = torch.float16  # T4/Colab: fp16 nhanh + tiết kiệm VRAM
    elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float16  # Apple Silicon: fp16 vào unified memory
    else:
        device = "cpu"
        dtype = torch.float32  # CPU fp32 ổn định và đôi khi còn nhanh hơn

    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=dtype, device_map=device, low_cpu_mem_usage=True
    )
    model.eval()

    _LLM_STATE = {"tokenizer": tokenizer, "model": model, "device": device}
    return _LLM_STATE


def _build_messages(
    text: str, emotion: str, arousal: str, history: list[dict], goal: str | None
) -> list[dict]:
    """Dựng messages theo chat template của Qwen.

    emotion: nhãn 7 giá trị; arousal: 'low'/'medium'/'high'; history: các
    lượt [{role:'user'|'assistant', content:str}] cũ.
    """
    system = (
        "Bạn là một người bạn tâm sự tiếng Việt ấm áp, giúp người dùng vui lên. "
        "Hãy trả lời NGẮN (1-3 câu), tự nhiên như nhắn tin, không liệt kê, "
        "không dùng markdown, không nhắc bạn là AI."
    )
    emotion_desc = f"Hệ thống phát hiện cảm xúc: {emotion}; mức năng lượng giọng nói: {arousal}."
    goal_desc = _GOAL_HINTS.get(str(goal), "")
    system = " ".join(x for x in [system, emotion_desc, goal_desc] if x)

    msgs = [{"role": "system", "content": system}]
    for turn in (history or [])[-_MAX_HISTORY_TURNS:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": text.strip() or "..."})
    return msgs


import time as _time  # noqa: E402  (đặt cuối để phần trên đọc như spec thuần)


def generate_reply(
    text: str, emotion: str, arousal: str, history: list[dict], goal: str | None = None
) -> str:
    """Sinh câu trả lời an ủi/động viên tiếng Việt dựa trên emotion + goal.

    Đầu vào: text (câu thoại), emotion (nhãn), arousal, history, goal.
    Đầu ra: chuỗi tiếng Việt non-empty.
    """
    state = _get_llm()
    tokenizer, model = state["tokenizer"], state["model"]

    messages = _build_messages(text, emotion, arousal, history, goal)
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer([prompt], return_tensors="pt").to(state["device"])
    max_new = 128

    started = _time.monotonic()
    try:
        import torch

        with torch.no_grad():
            out_ids = model.generate(
                **inputs,
                max_new_tokens=max_new,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = _time.monotonic() - started
        gen_ids = out_ids[0][inputs["input_ids"].shape[-1]:]
        reply = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
        if elapsed > 30.0:
            # Quá hạn pipeline — trả phản hồi ngắn thay vì để bị timeout.
            return "Mình ở đây, bạn yên tâm kể mình nghe nha."
    except Exception:  # pylint:disable=broad-except - mọi lỗi model vẫn trả str
        return "Mình ở đây, bạn yên tâm kể mình nghe nha."

    if not reply:
        reply = "Mình nghe bạn rồi, muốn kể thêm không nè?"
    return reply
