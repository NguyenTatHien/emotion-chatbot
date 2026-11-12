# Emotion Chatbot — Tài liệu Kỹ thuật (Technical Overview)

> Mục tiêu: người mới (dev/GV) nắm được **kiến trúc, luồng dữ liệu, quy ước vận hành** trong 10 phút, và biết chạy được hệ thống từ 0. Số liệu có nguồn ở Evidence Appendix [T.x].

---

## 1. Kiến trúc tổng thể

```
Browser (React :5174 dev)
   │ /api (vite proxy)
FastAPI backend (:8000) ── mode per-module: mock | local | remote ──► Model Server (Colab :8001, token-gated)
   │ speech(transcribe ∥ prosody) → safety (fail-closed) → emotion → (llm ∥ music)
   │            │
   ▼            ▼
PhoWhisper   CafeBERT + librosa-prosody        Qwen2.5-3B (local) / Qwen3-4B (Colab)
   + librosa
```

- **5 module có registry**: `speech, emotion, llm, music, safety` — swap `mock` → `mocks.*`, `local` → `modules.*`, `remote` → HTTP `clients/model_server.py`. [T1]
- **Thứ tự pipeline (bắt buộc của repo):** speech chạy song song → **safety TRƯỚC emotion (fail-closed)** → emotion → (llm ∥ music).
- **Frontend port 5174** (không phải 5173 — port bị chiếm bởi ứng dụng khác trên máy dev).

## 2. Các module ML

### 2.1 emotion — CafeBERT `BaoNhan/cafebert-UITVSMEC`
- 7 nhãn: Anger, Disgust, Enjoyment, Fear, Other, Sadness, Surprise; output `{label, probs}` (softmax đủ 7 khóa).
- Tokenizer `use_fast=False` — repo model chỉ có `sentencepiece.bpe.model`, thiếu `tokenizer.json` (transformers 5.x fast path chuyển sai TikToken). [T2]
- id2label tra cả key `int` và `str`; fallback theo vị trí (alphabet UIT-VSMEC) + `warnings.warn`.

### 2.2 speech — PhoWhisper `vinai/PhoWhisper-base` + librosa
- `transcribe(wav16k_mono)` → str (lỗi → rỗng, không raise).
- `extract_prosody`: RMS energy + pyin pitch (70-400Hz) + onset-based speech rate; arousal 3 mức heuristic (ngưỡng energy 0.02/0.08, pitch 250Hz).

### 2.3 llm — Qwen2.5-3B (local) / Qwen3-4B (Colab, env `LLM_MODEL_ID`)
- `enable_thinking=False` qua chat template (fallback template cũ không nhận kwarg).
- Generation: max_new_tokens=128, temperature 0.7, top_p 0.8, top_k 20; timeout do pipeline (`LLM_TIMEOUT`) — module không tự đo giờ.
- **Fail-safe:** mọi lỗi trong `generate_reply` (load/tokenize/generate) → `_SAFE_REPLY` cố định (trả str non-empty theo contract).

### 2.4 Quy ước bắt buộc
- **Lazy import** torch/transformers/librosa trong thân hàm — contract `test_import_is_light` chạy subprocess chặn.
- Device chain: `cuda > mps > cpu`; fp16 trên GPU.
- Env: `EMOTION_MODE/SPEECH_MODE/LLM_MODE ∈ {mock, local, remote}`; `LLM_MODEL_ID` (alias `LLM_MODEL`).

## 3. Model server Colab (mode `remote`)

- `colab/server_app.py` — FastAPI :8001; `/health` mở (không token), `/emotion /transcribe /prosody /generate` require header `X-Model-Server-Token`.
- Runbook: `colab/model_server_T4.ipynb` (T4 GPU, secrets `MODEL_SERVER_TOKEN` + `NGROK_AUTHTOKEN`, cell clone `-b main`, ngrok static domain).
- Verified live (2026-11-11): `/health` → `{"ok":true,"modules":["emotion","speech","llm"],"mocks":false}`; `/emotion` "hôm nay mình thấy hơi buồn quá…" → Sadness 96.2%. [T4]
- Hạn chế nền tảng: Colab free **ephemeral** (~90 phút idle/quota ngày) → backend tự fallback khi server mất.

## 4. Thí nghiệm & benchmark

| # | Thí nghiệm | Kết quả | Ghi chú |
|---|---|---|---|
| E3 | CafeBERT trên UIT-VSMEC test (n=693) | acc **0.6681**, macro-F1 **0.6209**, weighted 0.6636 | Đạt mục tiêu 0.627±0.007 (biên dưới); Anger F1 0.394 (40 mẫu) |
| E4 | Qwen3-4B zero-shot (n=150, seed=42) | v3: acc **0.5133**, macro-F1 **0.4505** | Parse 150/150; raw+greedy+verbalizer VI+EN |
| — | Majority-baseline | 0.2667 | always-Enjoyment |
| — | Ablation protocol | v1 (sampling, EN-only) 0.0588; v2 (confound persona) 0.0657 → v3 0.4505 | Protocol quyết định số đo |

**Protocol v3 (hợp lệ):** tải raw Qwen trong notebook thí nghiệm (không qua `/generate` — tránh persona-confound), `do_sample=False` (deterministic), `max_new_tokens=8`, strip `<tool_call>hink`, verbalizer EN+VI.
Tham chiếu ngoài: CNN baseline paper ~57.6%; ViSoBERT ~66%. [T5]
Notebook: `colab/experiment_E3_E4_ipynb` (code) + `_completed.ipynb` (có outputs).

## 5. Vận hành (ops)

| Việc | Lệnh/chỉ dẫn |
|---|---|
| Backend local | `cd backend && EMOTION_MODE=local SPEECH_MODE=local LLM_MODE=local .venv312/bin/uvicorn app.main:app --port 8000` |
| Frontend local | `cd frontend && npx -y pnpm@11.17.0 dev --port 5174` |
| Server Colab | `colab/model_server_T4.ipynb`: Runtime→T4 GPU → check `torch.cuda.is_available()` → Run all |
| Prod (Hiển) | VM + `docker-compose.prod.yml` + GitHub Actions images→deploy + Caddy; backend trỏ model server qua `MODEL_SERVER_URL` + `MODEL_SERVER_TOKEN` (handoff: `docs/HANDOFF-model-server-Quyen.md`) |
| Env Python | venv `.venv312` (3.12); transformers 5.x cần `sentencepiece protobuf accelerate` |

## 6. Đánh giá & kiểm thử hiện tại

- Contract tests: emotion 13/13, speech 4/4, llm 5/5; tổng 145 passed / 8 skipped. [T6]
- PR #1 (ML modules): **merged**; PR #2 (experiments + docs): OPEN chờ review.
- **Chưa verify [danh sách theo dõi]:** prod end-to-end sau khi Hiển cắm biến env; screenshot UI prod.

---

## Evidence Appendix

| # | Claim | Nguồn |
|---|---|---|
| T1 | Registry/pipeline/thứ tự safety-trước-emotion | `backend/app/registry.py`, `backend/app/pipeline.py` + bài test hợp đồng |
| T2 | use_fast=False / sentencepiece | `backend/modules/emotion.py` (comment + fix đã verify local) |
| T3 | Fail-safe LLM, tham số generation | `backend/modules/llm.py` |
| T4 | Health 200, Sadness 96.2% | curl test thật 2026-11-11 (session log) |
| T5 | Số E3/E4 + baselines | `colab/experiment_E3_E4_completed.ipynb` outputs; PACLING-2019; dinhthienan33 repo |
| T6 | Số test | pytest session log (2026-11-10) |
