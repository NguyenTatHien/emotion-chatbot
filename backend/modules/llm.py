"""Module sinh câu trả lời — Qwen chat (Qwen2.5-3B local / Qwen3-4B trên Colab).

Thiết kế:
- Import torch/transformers BÊN TRONG hàm (lazy) — bắt buộc vì
  `tests/contract/test_import_is_light.py` assert module nạp nhẹ.
- Tên model đọc từ env `LLM_MODEL_ID` (quy ước chính thức của repo, trùng với
  bản tham khảo `colab/reference_modules/llm.py`; alias cũ `LLM_MODEL` vẫn
  được nhận):
  - mặc định (laptop dev): `Qwen/Qwen2.5-3B-Instruct` (~6GB, chạy MPS/CPU đủ nhanh)
  - Colab T4: set `LLM_MODEL_ID=Qwen/Qwen3-4B` (~8GB fp16, đúng phương án
    của Thầy, còn dư VRAM cho CafeBERT + PhoWhisper trên cùng GPU)
- max_new_tokens=128 giữ độ trễ thực tế < 30s. Giới hạn cứng về thời gian
  nằm ở caller (`try_call` + LLM_TIMEOUT trong app/pipeline.py) — không
  tự chấm điểm thời gian trong module vì pipeline đã có fallback Gemini/canned.
- Lỗi (tải model, tokenize, generation) được in traceback rồi raise lên: backend coi đó là
  module lỗi và tự chuyển sang Gemini/câu soạn sẵn (`generate_with_fallback`). Trước đây lỗi
  bị nuốt và trả một câu cố định, khiến web lặp mãi câu đó mà không ai thấy nguyên nhân.

Cache model + tokenizer ở mức module (`_LLM_STATE`) — load 1 lần/lifetime.
"""

import logging

_logger = logging.getLogger("emotion_chatbot.modules.llm")

_LLM_STATE: dict | None = None
_DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct"

# Backend là nơi duy nhất quyết định độ dài lịch sử (bối cảnh + các lượt gần nguyên văn,
# tối đa ~30 tin). Đây chỉ là trần an toàn theo SỐ TIN (không phải số lượt) phòng khi gọi
# trực tiếp với history rất dài; cặp tin bối cảnh đầu (bắt đầu bằng `[BỐI CẢNH`) luôn được giữ.
_MAX_HISTORY_MESSAGES = 40
_CONTEXT_MARKER = "[BỐI CẢNH"

# Luật thẻ nhạc (backend tách thẻ khỏi câu trả lời).
_MUSIC_TAG_RULES = (
    "\nDòng đầu tiên của câu trả lời bắt buộc là [NHAC:CO] hoặc [NHAC:KHONG], "
    "sau đó xuống dòng rồi mới trả lời.\n"
    "Chọn [NHAC:CO] chỉ khi:\n"
    "(1) người dùng xin nghe nhạc, hỏi bài hát hoặc nhờ gợi ý bài; hoặc\n"
    "(2) người dùng đã buồn, lo sợ hoặc tức giận rõ rệt ở ít nhất 2 lượt gần đây "
    "(tính cả lượt hiện tại) và lượt ngay trước chưa được gợi ý nhạc.\n"
    "Mọi trường hợp khác chọn [NHAC:KHONG], nhất là: lượt đầu tiên; lần đầu kể một chuyện "
    "(hãy lắng nghe trước); cảm xúc Bình thường hoặc Vui vẻ; chào hỏi, cảm ơn, hỏi thông tin; "
    "người dùng đã nói không muốn nghe nhạc.\n"
    "Ghi chú của hệ thống cho biết đây là lượt thứ mấy.\n"
    "Ví dụ:\n"
    '"chào bạn" → [NHAC:KHONG]\n'
    '"mình đang phân vân không biết nên chọn hướng nào" → [NHAC:KHONG]\n'
    '"có bài nào nghe cho vui không" → [NHAC:CO]\n'
    'lượt thứ 3, hai lượt trước đều buồn: "mình sợ rớt môn lắm, chán ghê" → [NHAC:CO]\n'
    "Không nhắc tới thẻ này hay tự liệt kê bài hát trong câu trả lời. "
    "Nếu ghi chú của hệ thống có dòng 'Bài sẽ gợi ý kèm câu trả lời', hãy kết thúc bằng một "
    "câu ngắn, tự nhiên giới thiệu số nhạc đó (có thể nhắc tên một bài trong dòng ấy), không "
    "liệt kê hết, không hỏi người dùng muốn nói gì; không nhắc bài nào ngoài dòng ấy. "
    "Chỉ viết lời nói trực tiếp với người dùng, không viết nhận xét hay tóm tắt về họ."
)

# Chỉ thêm khi lịch sử thật sự mở đầu bằng ghi chú bối cảnh: nhắc tới nhãn ở mọi lượt khiến
# Qwen chép lại nhãn `[BỐI CẢNH ...]` và tự viết "tóm tắt" vào câu trả lời.
_CONTEXT_NOTE = (
    "Tin nhắn đầu tiên trong lịch sử là ghi chú của hệ thống (lượt thứ mấy, cảm xúc các lượt "
    "gần đây, lần gợi ý nhạc gần nhất, tóm tắt, giọng điệu nên dùng), không phải lời người "
    "dùng. Dùng nó để chọn thẻ nhạc, chọn giọng điệu và hiểu bối cảnh; không chép lại, không "
    "nhắc tới và không tự viết tóm tắt trong câu trả lời."
)

# Tên tiếng Việt của nhãn cảm xúc (khớp backend `app/constants.py` và frontend), để luật thẻ
# nhạc ("Bình thường", "Vui vẻ", "buồn"...) khớp với chữ mô hình thấy trong prompt.
_LABELS_VI = {
    "Anger": "Tức giận",
    "Disgust": "Khó chịu",
    "Enjoyment": "Vui vẻ",
    "Fear": "Lo sợ",
    "Other": "Bình thường",
    "Sadness": "Buồn",
    "Surprise": "Ngạc nhiên",
}

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

    # Quy ước env theo bản tham khảo upstream (colab/reference_modules/llm.py):
    # LLM_MODEL_ID là biến chính thức; LLM_MODEL giữ làm alias cho phép cũ.
    model_name = os.environ.get("LLM_MODEL_ID") or os.environ.get("LLM_MODEL", _DEFAULT_MODEL)
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
        model_name, dtype=dtype, device_map=device, low_cpu_mem_usage=True
    )
    model.eval()

    _LLM_STATE = {"tokenizer": tokenizer, "model": model, "device": device}
    return _LLM_STATE


def _emotion_label(emotion: object) -> str:
    """Chuẩn hoá tham số cảm xúc về nhãn: nhận dict {label, probs} (định dạng
    chuẩn của pipeline) hoặc chuỗi nhãn trần."""
    if isinstance(emotion, dict):
        return str(emotion.get("label", "Other"))
    return str(emotion or "Other")


def _emotion_note(emotion: object) -> str:
    """'Bình thường (73%)': tên tiếng Việt của nhãn kèm xác suất của nhãn đó (nếu có)."""
    label = _emotion_label(emotion)
    name = _LABELS_VI.get(label, label)
    probs = emotion.get("probs") if isinstance(emotion, dict) else None
    prob = (probs or {}).get(label)
    try:
        return f"{name} ({float(prob):.0%})" if prob is not None else name
    except (TypeError, ValueError):
        return name


def _limit_history(history: list[dict]) -> list[dict]:
    """Chỉ chặn trần theo số tin; luôn giữ cặp tin bối cảnh đầu nếu có."""
    if len(history) <= _MAX_HISTORY_MESSAGES:
        return history
    first = str((history[0] or {}).get("content") or "")
    if first.lstrip().startswith(_CONTEXT_MARKER):
        return history[:2] + history[-(_MAX_HISTORY_MESSAGES - 2):]
    return history[-_MAX_HISTORY_MESSAGES:]


def _build_messages(
    text: str, emotion: object, arousal: str, history: list[dict], goal: str | None
) -> list[dict]:
    """Dựng messages theo chat template của Qwen.

    emotion: dict {label, probs} (chuỗi lượt chat của pipeline) hoặc chuỗi
    nhãn; arousal: 'low'/'medium'/'high'; history: các lượt
    [{role:'user'|'assistant', content:str}] cũ.
    """
    system = (
        "Bạn là một người bạn tâm sự tiếng Việt ấm áp, đồng hành, lắng nghe, "
        "trả lời theo đúng tâm trạng người dùng. "
        "Hãy trả lời NGẮN (1-3 câu), tự nhiên như nhắn tin, không liệt kê, "
        "không dùng markdown, không nhắc bạn là AI. "
        "Làm theo dòng \"Giọng điệu nên dùng\" trong ghi chú của hệ thống. "
        "Không nhắc tên nhãn cảm xúc hay con số phần trăm. "
        "Bạn là chatbot đồng hành, không đóng vai một người có đời sống riêng: "
        "không tự kể chuyện bản thân và không bịa thông tin về mình "
        "(học hành, công việc, tuổi, nơi ở, chuyện riêng); chỉ tập trung vào người dùng. "
        + _MUSIC_TAG_RULES
    )
    emotion_desc = f"Cảm xúc lượt hiện tại (hệ thống đo): {_emotion_note(emotion)}."
    if arousal:
        emotion_desc += f" Mức năng lượng giọng nói: {arousal}."
    goal_desc = _GOAL_HINTS.get(str(goal), "")
    limited = _limit_history(history or [])
    first = str((limited[0] or {}).get("content") or "") if limited else ""
    context_note = _CONTEXT_NOTE if first.lstrip().startswith(_CONTEXT_MARKER) else ""
    system = "\n".join(x for x in [system, context_note, emotion_desc, goal_desc] if x)

    msgs = [{"role": "system", "content": system}]
    for turn in limited:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": text.strip() or "..."})
    return msgs


def generate_reply(
    text: str, emotion: object, arousal: str, history: list[dict], goal: str | None = None
) -> str:
    """Sinh câu trả lời an ủi/động viên tiếng Việt dựa trên emotion + goal.

    Đầu vào: text (câu thoại), emotion (dict {label, props} hoặc nhãn),
    arousal ('' nếu không có), history, goal.
    Đầu ra: chuỗi tiếng Việt non-empty. Lỗi (tải model/tokenize/generate) được ghi
    traceback rồi raise để backend chuyển sang nguồn dự phòng.
    """
    try:
        state = _get_llm()
        tokenizer, model = state["tokenizer"], state["model"]

        messages = _build_messages(text, emotion, arousal, history, goal)
        # Qwen3 có chế độ "thinking" bật mặc định — phải tắt (tham khảo upstream
        # reference_modules/llm.py). Template Qwen2.5 không nhận kwarg này,
        # nên gọi thử và bỏ qua nếu chưa hỗ trợ.
        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except (TypeError, KeyError):
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        inputs = tokenizer([prompt], return_tensors="pt").to(state["device"])

        import torch

        with torch.no_grad():
            out_ids = model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=True,
                temperature=0.7,
                top_p=0.8,  # theo khuyến nghị Qwen3 cho chế độ không suy luận
                top_k=20,
                pad_token_id=tokenizer.eos_token_id,
            )
        gen_ids = out_ids[0][inputs["input_ids"].shape[-1]:]
        reply = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
    except Exception:
        # In đủ traceback ra log (Colab/uvicorn) để biết nguyên nhân, rồi raise để backend
        # dùng Gemini thay vì trả một câu cố định.
        _logger.exception("generate_reply lỗi")
        raise
    return reply or "Mình nghe bạn rồi, muốn kể thêm không nè?"
