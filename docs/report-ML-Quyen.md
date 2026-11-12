# Báo cáo phần ML — Nguyễn Ngọc Mỹ Quyên (25MS23295)

> Project: emotion-chatbot (NLP501). Phạm vi: 3 module ML (`backend/modules/{emotion,speech,llm}.py`) + model server Colab + thí nghiệm đánh giá E3/E4.
> Tất cả số liệu trong tài liệu này là kết quả **lưu trong notebook `colab/experiment_E3_E4_completed.ipynb`** (đã chạy, có outputs).

---

## 1. Kiến trúc 3 module ML

| Module | Model | Vai trò trong pipeline |
|---|---|---|
| `emotion` | CafeBERT `BaoNhan/cafebert-UITVSMEC` (7 nhãn) | Phân loại cảm xúc văn bản → `{label, probs}` |
| `speech` | PhoWhisper `vinai/PhoWhisper-base` + librosa | ASR (`transcribe`) + prosody (`extract_prosody` → arousal low/medium/high) |
| `llm` | Qwen2.5-3B (local) / Qwen3-4B (Colab T4, env `LLM_MODEL_ID`) | Sinh câu trả lời an ủi/tích cực theo emotion + goal |

**Quyết định thiết kế chính:**
- **Lazy import** (torch/transformers/librosa trong thân hàm): module nạp nhẹ, khớp contract `test_import_is_light`.
- **Fail-safe theo từng tầng**: LLM lỗi → `_SAFE_REPLY`; audio lỗi → chuỗi rỗng; text rỗng → phân bố đều, `Other`. Không raise xuyên suốt pipeline.
- **Chọn device** `cuda > mps > cpu` cho cả 3 module; fp16 trên GPU.
- **CafeBERT tokenizer `use_fast=False`**: repo model chỉ có `sentencepiece.bpe.model` (không `tokenizer.json`) — fast path của transformers 5.x chuyển sai TikToken extractor.
- **Qwen3**: `enable_thinking=False` qua chat template (fallback template cũ không nhận kwarg); max_new_tokens=128, timeout thực tế do pipeline (`LLM_TIMEOUT`) kiểm soát, không chấm trong module.

**Kiểm thử:** contract tests 13/13 (emotion) + 4/4 (speech) + 5/5 (llm); toàn bộ suite 145 passed / 8 skipped.

## 2. Thí nghiệm E3/E4 — phân tích chi tiết

### 2.1 E3 — CafeBERT fine-tuned trên UIT-VSMEC test (n = 693)

| Metric | Kết quả | Mục tiêu tham chiếu |
|---|---|---|
| accuracy | **0.6681** | — |
| **macro-F1** | **0.6209** | 0.627 ± 0.007 → **đạt** (0.6209 ∈ [0.620, 0.634]) |
| weighted-F1 | 0.6636 | — |

F1 từng lớp: Enjoyment **0.766**, Sadness 0.761, Disgust 0.633, Fear 0.652, Surprise 0.571, Other 0.568, **Anger 0.394** (support chỉ 40).

- Lệch lớp kéo macro-F1 xuống: Anger (40 mẫu) kém nhất; `Other` là lớp rác khó học (129 mẫu, precision 0.626 / recall 0.519).
- Confusion matrix: hình `E3_confusion.png` (bản đầy đủ trong notebook completed).

### 2.2 E4 — Qwen3-4B zero-shot (n = 150, seed = 42, sample cố định)

| Protocol | accuracy | macro-F1 | Đánh giá |
|---|---|---|---|
| v1 — server `/generate`, sampling 0.7, nhãn EN | 0.2267 | 0.0588 | **hết protocol**: trả lời không chứa tên nhãn → toàn fallback `Other` |
| v2 — cùng trên, verbalizer VI+EN | 0.2333 | 0.0657 | **confound**: endpoint bọc system-prompt chatbot ("Hệ thống phát hiện cảm xúc: Other") → 148/150 trả "Other" |
| **v3 — raw Qwen local, greedy (temperature 0), verbalizer VI+EN** | **0.5133** | **0.4505** | **hợp lệ**: parse 150/150, phân bố đủ 7 nhãn |
| Majority-baseline (always-Enjoyment) | 0.2667 | — | mốc tham chiếu |

### 2.3 Kết luận

1. **Fine-tuned chuyên biệt vượt LLM tổng quát zero-shot trong miền hẹp** (+0.17 macro-F1: 0.6209 vs 0.4505) — cả hai đều vượt majority-baseline.
2. **Protocol quyết định số đo**: v1/v2 → v3 (0.059 → 0.4505 macro-F1) chỉ nhờ sửa protocol (bỏ wrapper, decoding deterministic, verbalizer song ngữ). Kết quả zero-shot công bố trên LLM generation tự do cần kiểm tra cấu hình sampling/wrapper — kết luận có căn cứ:
   - *Tunstall, von Werra, Wolf — NLP with Transformers (O'Reilly 2022), tr.265–271*: tên nhãn có ngữ nghĩa quyết định độ chính xác zero-shot; hypothesis template nhạy cảm.
   - *Alammar, Grootendorst — Hands-On Large Language Models (O'Reilly 2024), tr.195*: output classification cần constrain trong sampling process, chịu ảnh hưởng `temperature`/`top_p`.
3. **Hạn chế**: (i) E4 đo trên n=150 (latency LLM) — đủ lớn nhưng không toàn tập; (ii) lớp thiểu số E3 (Anger) F1 0.394; (iii) Qwen zero-shot với nhãn tiếng Việt social media chưa được tune — không phải ceiling của LLM.

## 3. Model server Colab (mode `remote`)

- Notebook `colab/model_server_T4.ipynb`: FastAPI server (:8001) + ngrok static domain, 3 model thật (`mocks: false`), token header `X-Model-Server-Token`.
- Verified: `/health` → `{"ok":true,"modules":["emotion","speech","llm"],"mocks":false}`; `/emotion` "hôm nay mình thấy hơi buồn quá…" → **Sadness 96.2%**; `/generate` → câu an ủi tiếng Việt tự nhiên.
- Giới hạn: Colab free ~90 phút idle/quota ngày → server ephemeral; backend tự fallback khi mất server.

## 4. Sản phẩm của Quyên

1. `backend/modules/{emotion,speech,llm}.py` — merged vào `main` (PR #1).
2. `colab/model_server_T4.ipynb` — model server T4 runbook.
3. `colab/experiment_E3_E4.ipynb` (+ `*_completed.ipynb` có outputs) — thí nghiệm E3/E4.
4. Bằng chứng vận hành: logs health/emotion/generate + test prod.
