# ANSWER

## TL;DR (≤ 5 行, AI 5 秒可读)

- answer: emotion-chatbot là chatbot cảm xúc tiếng Việt bằng giọng nói: speech(transcribe∥prosody) → safety fail-closed → emotion → (llm∥music), 5 module swap qua registry mock|local|remote, backend FastAPI :8000 + frontend React :5174 + Colab model server :8001. Trên main da1b8a7 có 3 delta: fix context-leak (0500f48 — xoá nhãn [BỐI CẢNH] khỏi reply + dùng dữ kiện thay tóm tắt), fix no-persona (da1b8a7 — cấm LLM bịa chuyện bản thân), feat contextual-music-memory (e66d725 — memory.py + music_tag + music_decision).
- scope_in: [business scope & commitments; architecture diagram + registry swap; end-to-end pipeline flow with safety ordering; all 5 module entry points + interfaces; 3 recent git deltas with diff evidence].
- scope_out: [Gemini fallback internals (summarize prompt); session.py store internals (MemorySnapshot/SessionState); feedback route contract; frontend component tree beyond ChatView→useChat; CI/CD pipeline (covered in prior cache); ML model weights/training internals].
- stale_check: git_head=da1b8a7; verify with `git -C /Users/quiniu/fsb/NLP/final_project/emotion-chatbot diff HEAD -- backend/app/pipeline.py backend/app/registry.py backend/app/memory.py backend/modules/llm.py backend/app/music_tag.py docs/BUSINESS-overview.md docs/TECHNICAL-overview.md`.

## Frontmatter
created: 2026-11-13T16:51:26
question: Complete system-level understanding of emotion-chatbot: business scope, architecture, pipeline flow, module interfaces, recent deltas on main da1b8a7.
posterior_final: 0.95
rg_calls_used: 3
engine: opencode
git_head: da1b8a7
git_branch: view-latest-main
files_verified_mtime:
  docs/BUSINESS-overview.md: 2026-11-13T16:49:11
  docs/TECHNICAL-overview.md: 2026-11-13T16:49:11
  backend/app/pipeline.py: 2026-11-13T16:49:11
  backend/app/registry.py: 2026-11-10T14:09:14
  backend/app/routes/chat.py: 2026-11-10T11:52:30
  backend/app/memory.py: 2026-11-13T16:49:11
  backend/app/music_tag.py: 2026-11-13T16:49:11
  backend/modules/emotion.py: 2026-11-10T14:18:32
  backend/modules/speech.py: 2026-11-10T14:18:32
  backend/modules/llm.py: 2026-11-13T16:49:11
  backend/modules/safety.py: 2026-11-10T11:52:30
  backend/modules/music.py: 2026-11-10T11:52:30
  backend/mocks/music.py: 2026-11-10T11:52:30
  backend/app/gemini.py: 2026-11-13T16:49:11
  backend/app/config.py: 2026-11-13T16:49:11

## Spec (formal-spec; PRE / POST / INV / ERR / KILL when applicable)

PRE: Repo @ da1b8a7, branch view-latest-main. Stack: React :5174 (vite proxy /api), FastAPI :8000, Colab model server :8001 (token-gated). Modules: speech, emotion, llm, music, safety — registry modes mock|local|remote.
POST: ∀ chat request: speech(transcribe∥prosody) → safety(fail-closed) → emotion → (llm∥music) ∨ safety-reply. ∀ module: registry.get(name) returns callable per mode. ∀ LLM reply: music tag + context-label stripped before user sees it.
INV1: Pipeline order: speech ∥ → safety BEFORE emotion (fail-closed) → emotion → (llm ∥ music) [pipeline.py:145-251].
INV2: Safety risk=true ⇒ reply = safety_msg, emotion=None, songs=[] [pipeline.py:209-210,262-265].
INV3: Registry: mock→mocks.*, local→modules.*, remote→clients.model_server.*; safety/music ∉ REMOTE_FUNCS [registry.py:32,69-78].
INV4: ∀ LLM/Gemini reply: split_music_tag strips [NHAC:CO/KHONG] + [BỐI CẢNH] lines [music_tag.py:49-74].
INV5: Context pair (memory) injected only from turn 2 (snap.total > 0) [memory.py:82-83].
INV6: Lazy import: torch/transformers/librosa inside function bodies, never module-top [modules/emotion.py:41-42, modules/speech.py:26-27, modules/llm.py:91-92].
ERR: Module error/timeout → try_call returns (None, warning) → fallback (emotion=Other, LLM=_SAFE_REPLY or Gemini or canned) [pipeline.py:39-50,104-127].
KILL: Invalid *_MODE raises ValueError at create_app() [config.py:75-78, main.py:31-32].

## File map (scored + relationships)

### Scored files.

| rank | score | file | role | evidence (file:line) |
|------|-------|------|------|----------------------|
| 1 | 0.98 | backend/app/pipeline.py | Pipeline orchestrator: speech∥→safety→emotion→(llm∥music), fallback chain, music decision | pipeline.py:130-304 |
| 2 | 0.95 | backend/app/registry.py | Module registry: resolves impl by mode (mock/local/remote/gemini), override for tests | registry.py:58-78 |
| 3 | 0.93 | backend/app/routes/chat.py | POST /api/chat endpoint: multipart form, audio normalize, delegates to pipeline.handle_chat | chat.py:23-90 |
| 4 | 0.92 | backend/app/memory.py | Conversation memory: context pair (facts+summary+music profile), background Gemini summary | memory.py:81-113,116-150 |
| 5 | 0.90 | backend/app/music_tag.py | Splits [NHAC:CO/KHONG] tag + strips [BỐI CẢNH] context-label lines from LLM reply | music_tag.py:49-74 |
| 6 | 0.90 | backend/modules/llm.py | Qwen2.5-3B/Qwen3-4B generate_reply: system prompt with music rules, context note, no-persona clause | llm.py:185-232,157-165 |
| 7 | 0.88 | backend/modules/emotion.py | CafeBERT predict_emotion: 7-label softmax, lazy load, device chain, id2label fallback | emotion.py:95-143 |
| 8 | 0.85 | backend/modules/speech.py | PhoWhisper transcribe + librosa extract_prosody (arousal heuristic) | speech.py:40-112 |
| 9 | 0.82 | backend/app/gemini.py | Gemini generate_reply + summarize: system prompt mirrors llm.py rules, conditional CONTEXT_NOTE | gemini.py:22-55,108-120 |
| 10 | 0.80 | docs/BUSINESS-overview.md | Business scope: voice emotion chatbot, 7 labels, macro-F1 0.6209, ephemeral Colab, honest limits | BUSINESS-overview.md:7-63 |
| 11 | 0.80 | docs/TECHNICAL-overview.md | Architecture diagram, pipeline order, module specs, ops commands, experiment results | TECHNICAL-overview.md:9-92 |
| 12 | 0.75 | backend/modules/safety.py | Safety stub: check_safety(text) → {risk, message}, raises NotImplementedError (unassigned) | safety.py:7-14 |
| 13 | 0.70 | backend/modules/music.py | Music recommend: recommend(label, arousal, goal, k) → list[dict], reads songs.csv | music.py:7 |
| 14 | 0.65 | backend/app/config.py | Settings: MODEL_MODE, per-module modes, validate_remote, safety/music ∉ remote | config.py:11-101 |
| 15 | 0.60 | frontend/src/hooks/useChat.ts | Frontend hook: useChat(sessionId, goal) → manages chat state, posts to /api/chat | useChat.ts:41 |
| 16 | 0.55 | frontend/src/components/chat/ChatView.tsx | Main UI component: imports useChat, renders MessageList, SafetyAlert | ChatView.tsx:3,59 |
| 17 | 0.50 | frontend/src/components/system/SafetyAlert.tsx | Safety alert component rendered when response.safety=true | SafetyAlert.tsx:4 |
| 18 | 0.45 | backend/mocks/music.py | Mock music: reads data/songs.csv, simulate_latency | mocks/music.py:21 |

### Relationships (formal-spec).

CONTRACTS:
  - F := scored_files.
  - rel: F × F × KIND → bool. KIND ∈ { imports, calls, inherits, configures, tests, references, defines, triggered_by, depends_on }.

EDGES:
  rel(backend/app/routes/chat.py, backend/app/pipeline.py, calls) ⇒ chat.py:10,77
  rel(backend/app/pipeline.py, backend/app/registry.py, calls) ⇒ pipeline.py:17,96,151,157,192,214,228
  rel(backend/app/pipeline.py, backend/app/memory.py, calls) ⇒ pipeline.py:17,203,285
  rel(backend/app/pipeline.py, backend/app/music_tag.py, calls) ⇒ pipeline.py:20,105,122
  rel(backend/app/pipeline.py, backend/app/fallbacks.py, calls) ⇒ pipeline.py:17,201,127
  rel(backend/app/pipeline.py, backend/app/gemini.py, calls) ⇒ pipeline.py:17,76-127
  rel(backend/app/registry.py, backend/app/config.py, depends_on) ⇒ registry.py:9,49,64
  rel(backend/app/registry.py, backend/app/clients/model_server.py, calls) ⇒ registry.py:72-74
  rel(backend/app/registry.py, backend/modules/emotion.py, references) ⇒ registry.py:76-78
  rel(backend/app/registry.py, backend/modules/speech.py, references) ⇒ registry.py:76-78
  rel(backend/app/registry.py, backend/modules/llm.py, references) ⇒ registry.py:76-78
  rel(backend/app/registry.py, backend/modules/safety.py, references) ⇒ registry.py:76-78
  rel(backend/app/registry.py, backend/modules/music.py, references) ⇒ registry.py:76-78
  rel(backend/app/memory.py, backend/app/gemini.py, calls) ⇒ memory.py:12,142-143
  rel(backend/app/memory.py, backend/app/session.py, depends_on) ⇒ memory.py:16,113,121,124
  rel(backend/app/music_tag.py, backend/app/memory.py, references) ⇒ music_tag.py:29,38-46 (CONTEXT_MARKER)
  rel(backend/modules/llm.py, backend/app/music_tag.py, references) ⇒ llm.py:31,34-52,143 (tag rules + context marker)
  rel(backend/app/gemini.py, backend/app/music_tag.py, references) ⇒ gemini.py:22-55 (mirrors tag rules)
  rel(frontend/src/components/chat/ChatView.tsx, frontend/src/hooks/useChat.ts, calls) ⇒ ChatView.tsx:3,59
  rel(frontend/src/hooks/useChat.ts, frontend/src/hooks/chat-state.ts, imports) ⇒ useChat.ts:14
  rel(frontend/src/components/chat/BotMessage.tsx, frontend/src/components/system/SafetyAlert.tsx, imports) ⇒ BotMessage.tsx:4,26

### Topology.

  - entry_point := frontend/src/components/chat/ChatView.tsx:59 (useChat) → POST /api/chat [chat.py:23] → pipeline.handle_chat [pipeline.py:130].
  - critical_path := ChatView.tsx → useChat.ts → /api/chat (chat.py:23) → audio.normalize (chat.py:70) → pipeline.handle_chat (pipeline.py:130) → registry.get (registry.py:58) → {modules/*, mocks/*, clients/model_server.py} → memory.build_history (memory.py:111) → generate_with_fallback (pipeline.py:76) → split_music_tag (music_tag.py:49) → store.append_turn (pipeline.py:268) → ChatResponse (pipeline.py:296).
  - leaf_files := { backend/modules/emotion.py, backend/modules/speech.py, backend/modules/llm.py, backend/modules/safety.py, backend/modules/music.py, backend/mocks/music.py, frontend/src/components/system/SafetyAlert.tsx, backend/app/config.py }.

## Behavior (input → process → output, 运行时视图)

- input: Multipart form POST /api/chat with fields: session_id (1-64 chars), message (text, optional), transcript_hint (browser-side ASR text, optional), goal (∈ {xoa_diu, nang_mood, tap_trung, giai_toa}, optional), audio_file (WAV upload, optional) [chat.py:24-30,34-42]. Frontend ChatView.tsx:59 calls useChat which posts FormData to /api/chat [useChat.ts:41].
- process:
  (1) chat.py validates session_id, message length, goal; reads audio via audio.read_limited (MAX_AUDIO_MB); normalizes to WAV 16kHz mono via ffmpeg [chat.py:31-75].
  (2) pipeline.handle_chat: if audio_path, runs speech.transcribe ∥ speech.extract_prosody via asyncio.gather [pipeline.py:148-161]. Transcript = transcribe result or transcript_hint fallback [pipeline.py:163-177]. No usable text ⇒ NoUsableInput exception [pipeline.py:183-186].
  (3) Safety runs FIRST (fail-closed): try_call(safety, text) → {risk, message}; error/timeout → fallback keyword_safety [pipeline.py:191-201]. If risk=true: reply = safety_msg, skip emotion/llm/music [pipeline.py:209-210].
  (4) If not risk: emotion = try_call(emotion, text) → {label, probs}; invalid → fallback_emotion [pipeline.py:213-219].
  (5) Music decision: if goal (chip) → run llm ∥ music in parallel [pipeline.py:237-242]; else run llm first, if LLM output has [NHAC:CO] tag → run music [pipeline.py:243-251]. MusicDecision ∈ {safety, chip, llm, llm_no, no_tag} [pipeline.py:206,238,248,251].
  (6) LLM chain: generate_with_fallback tries registry.get("llm") → if empty/error, tries Gemini (if API key + not already gemini mode) → if empty, canned_reply [pipeline.py:76-127].
  (7) ∀ LLM/Gemini result: split_music_tag strips [NHAC:CO/KHONG] tag + [BỐI CẢNH] context-label lines [pipeline.py:105,122, music_tag.py:49-74].
  (8) memory.build_history: from turn 2, injects context pair [user: CONTEXT_HEADER+facts, assistant: "Mình nhớ rồi."] + verbatim unsummarized turns [memory.py:81-108]. Background: maybe_schedule_summary runs Gemini summarize every HISTORY_TURNS+SUMMARY_BATCH_TURNS [memory.py:116-150].
  (9) store.append_turn persists SessionTurn (turn_id, user_text, reply, emotion, songs, safety, goal, llm_backend, music_decision) [pipeline.py:268-283].
- output: ChatResponse{turn_id, reply, transcript, emotion: {label, probs, arousal}|null, songs: list[Song]|[], safety: bool, meta: {llm_backend, model_mode, modules, degraded, latency_ms, warnings, music_decision}} [pipeline.py:296-304, schemas.py].
- side_effects: Writes session turns to in-memory store (session.py); writes feedback.jsonl (FEEDBACK_PATH); background Gemini API call for summarization (network egress); Colab model server HTTP calls when remote mode (network egress, token-gated); temporary audio files created/cleaned per request [chat.py:61-91, pipeline.py:268, memory.py:142-143].

## Findings (cite file:line)

### (1) Business scope & commitments

- Product: Vietnamese voice emotion chatbot — user speaks, system transcribes → detects emotion → responds as a warm friend [BUSINESS-overview.md:7-9].
- Input modality: voice OR text; responses short, natural like texting [BUSINESS-overview.md:11-12].
- Problem solved: (a) user needs listener not advisor; (b) emotion not always in words → prosody detection; (c) psychological safety → safe-reply layer (fail-safe) [BUSINESS-overview.md:16-20].
- Target users: young people needing daily stress relief; NLP501 course end-to-end ML exercise [BUSINESS-overview.md:22].
- Quality results: CafeBERT macro-F1 0.6209 (meets target 0.627±0.007 lower bound); LLM zero-shot baseline ~0.45 (+0.17 from fine-tune); E2E verified: "hôm nay mình thấy hơi buồn quá" → Sadness 96.2%, health 200 OK [BUSINESS-overview.md:34-38].
- Team: Quyên (ML: 3 models + Colab + experiments); Hiển (FE/BE/infra: React, FastAPI, deploy) [BUSINESS-overview.md:42-43].
- Honest limits: (1) Colab server ephemeral (~90 min idle/quota); (2) Anger F1 0.394 (40 samples, rare label); (3) Zero-shot LLM n=150, ±0.05 confidence interval [BUSINESS-overview.md:47-49].
- Unverified: prod end-to-end after env handoff — marked [CHƯA XÁC MINH] [BUSINESS-overview.md:63].

### (2) Architecture diagram & module registry + swap mechanism

- Architecture diagram [TECHNICAL-overview.md:9-18]:
  ```
  Browser (React :5174 dev)
     │ /api (vite proxy)
  FastAPI backend (:8000) ── mode per-module: mock|local|remote ──► Model Server (Colab :8001, token-gated)
     │ speech(transcribe ∥ prosody) → safety (fail-closed) → emotion → (llm ∥ music)
     │            │
     ▼            ▼
  PhoWhisper   CafeBERT + librosa-prosody        Qwen2.5-3B (local) / Qwen3-4B (Colab)
     + librosa
  ```
- 5 modules with registry: speech, emotion, llm, music, safety — swap mock→mocks.*, local→modules.*, remote→HTTP clients/model_server.py [TECHNICAL-overview.md:20, registry.py:76-78].
- Pipeline order (mandatory): speech parallel → safety BEFORE emotion (fail-closed) → emotion → (llm ∥ music) [TECHNICAL-overview.md:21, pipeline.py:145-251].
- Frontend port 5174 (not 5173 — port conflict on dev machine) [TECHNICAL-overview.md:22].
- Registry swap mechanism [registry.py:58-78]:
  - `get(name, func)` resolves callable by mode: gemini → gemini.generate_reply; remote → model_server client; mock → mocks.*; local → modules.*.
  - `REMOTE_FUNCS = {"emotion", "speech", "llm"}` — safety and music CANNOT be remote [registry.py:32,69-71].
  - `override(name, fn)` / `reset_overrides()` for test injection [registry.py:81-87].
  - `DEFAULT_FUNCS` maps module→function name: emotion=predict_emotion, speech=transcribe, safety=check_safety, llm=generate_reply, music=recommend [registry.py:13-19].

### (3) Request pipeline flow end-to-end

- Frontend: ChatView.tsx imports useChat(sessionId, goal) [ChatView.tsx:3,59]; useChat posts FormData to /api/chat [useChat.ts:41]; BotMessage renders SafetyAlert when safety=true [BotMessage.tsx:26].
- FastAPI route: POST /api/chat accepts multipart form (session_id, message, transcript_hint, goal, audio_file) [chat.py:23-30]; validates inputs [chat.py:33-42]; reads+normalizes audio via audio.read_limited + audio.normalize [chat.py:44-75].
- Pipeline orchestration (handle_chat) [pipeline.py:130-304]:
  - Step 0 (if audio): speech.transcribe ∥ speech.extract_prosody via asyncio.gather [pipeline.py:148-161].
  - Step 1: text = message > transcript > transcript_hint; empty ⇒ NoUsableInput [pipeline.py:180-186].
  - Step 2: SAFETY FIRST (fail-closed) — try_call(safety, text); error ⇒ fallback keyword_safety [pipeline.py:191-201]. risk=true ⇒ safety reply, skip rest [pipeline.py:209-210].
  - Step 3: emotion = try_call(emotion, text); invalid ⇒ fallback_emotion [pipeline.py:213-219].
  - Step 4: music decision — goal chip ⇒ llm ∥ music parallel; no chip ⇒ llm first, music if [NHAC:CO] tag [pipeline.py:221-251].
  - Step 5: generate_with_fallback — llm → Gemini → canned [pipeline.py:76-127].
  - Step 6: split_music_tag strips tags + context labels from reply [pipeline.py:105,122].
  - Step 7: store.append_turn + maybe_schedule_summary [pipeline.py:268-285].
  - Return ChatResponse with Meta (llm_backend, modules, degraded, latency_ms, warnings, music_decision) [pipeline.py:296-304].
- Safety fail-closed ordering: safety runs BEFORE emotion; if safety errors/times out, keyword_safety fallback is used (fail-closed = default to checking) [pipeline.py:188-201]. If risk=true, emotion and music are skipped entirely [pipeline.py:209-210,262-265].

### (4) Each module's implementation entry point + interfaces

- **emotion** — `predict_emotion(text: str) → {label: str, probs: dict[str,float]}` [emotion.py:95]. Model: CafeBERT `BaoNhan/cafebert-UITVSMEC`, 7 labels (Anger, Disgust, Enjoyment, Fear, Other, Sadness, Surprise) [emotion.py:19,24]. Lazy import torch/transformers inside function [emotion.py:41-42,103-104]. Device chain: cuda > mps > cpu [emotion.py:49-54]. Tokenizer `use_fast=False` (sentencepiece only) [emotion.py:47]. Caches model in `_STATE` [emotion.py:22,86-92]. Empty text → uniform distribution, label "Other" [emotion.py:112-114]. Max 256 tokens truncation [emotion.py:122].
- **speech** — two functions:
  - `transcribe(wav_path: str) → str` [speech.py:40]. Model: PhoWhisper `vinai/PhoWhisper-base` [speech.py:17]. Error → empty string (no raise) [speech.py:50-53].
  - `extract_prosody(wav_path: str) → {arousal: "low"|"medium"|"high", pitch_mean: float, energy_rms: float, speech_rate: float}` [speech.py:58]. librosa: RMS energy + pyin pitch (70-400Hz) + onset-based speech rate [speech.py:69-92]. Arousal heuristic: energy < 0.02 → low; > 0.08 or pitch > 250Hz → high; else medium [speech.py:100-105].
- **llm** — `generate_reply(text, emotion, arousal, history, goal=None) → str` [llm.py:185-186]. Model: Qwen2.5-3B (local default) / Qwen3-4B (Colab, env LLM_MODEL_ID) [llm.py:22,96]. Generation: max_new_tokens=128, temp=0.7, top_p=0.8, top_k=20 [llm.py:221-226]. `enable_thinking=False` with fallback [llm.py:204-213]. ALL errors → `_SAFE_REPLY` ("Mình ở đây, bạn yên tâm kể mình nghe nha.") [llm.py:230-231]. System prompt includes music tag rules [llm.py:34-52], no-persona clause [llm.py:161-163], conditional context note [llm.py:56-61,172].
- **safety** — `check_safety(text: str) → {risk: bool, message: str|None}` [safety.py:7]. STUB: raises NotImplementedError("Người 3 phụ trách") [safety.py:14]. Pipeline falls back to keyword_safety on error [pipeline.py:197-201].
- **music** — `recommend(label, arousal, goal, k=5) → list[dict]` [music.py:7]. Mock reads from `data/songs.csv` [mocks/music.py:1,21]. Mode ∈ {mock, local} only (NOT remote) [registry.py:32,69-71].

### (5) Recent deltas on main da1b8a7

#### 5a. fix: context-leak (commit 0500f48, PR #4)

Problem: Qwen 4B copied the `[BỐI CẢNH CUỘC TRÒ CHUYỆN]` label into its reply and auto-wrote a user summary at the start [0500f48 commit message].

Changes (11 files, +327 -51):
- **music_tag.py**: Added `_drop_context_lines()` — strips lines starting with folded "[boi canh cuoc tro chuyen" from LLM output; called within `split_music_tag()` [music_tag.py:29,38-46,69]. This is a backend safety net: even if the model copies the label, the user never sees it.
- **memory.py**: Context message changed from "tóm tắt các lượt trước" to "ghi chú của hệ thống" [memory.py:22-23]. Added `_facts()` (turn number, recent emotions, last music turn) and `_recent_emotions()` [memory.py:49-78]. Context pair injected only from turn 2 (`snap.total == 0 → None`) [memory.py:82-83].
- **gemini.py**: Removed explicit `[BỐI CẢNH]` label mention from SYSTEM_PROMPT; added `CONTEXT_NOTE` conditionally (only when history starts with context pair) [gemini.py:39-55,118-120]. Added `has_context_pair()` and `emotion_note()` [gemini.py:41-53].
- **modules/llm.py**: Same changes — removed label from `_MUSIC_TAG_RULES`, added `_CONTEXT_NOTE` conditionally, added `_emotion_note()`, `_LABELS_VI` dict [llm.py:34-61,126-135,160-173].
- Music tag rules refined: [NHAC:CO] only when (1) user asks for music, or (2) user sad/fear/angry for ≥2 recent turns AND previous turn had no music [llm.py:37-43, gemini.py:30-36].

#### 5b. fix: no-persona (commit da1b8a7, PR #5)

Problem: Qwen impersonated a human ("tôi đang tốt nghiệp đại học, làm part-time") — prompt "người bạn tâm sự, không nhắc bạn là AI" caused small model to roleplay a person with a life [da1b8a7 commit message].

Changes (4 files, +23 -5):
- **gemini.py SYSTEM_PROMPT**: Added "Bạn là chatbot đồng hành, không đóng vai một người có đời sống riêng: không tự kể chuyện bản thân và không bịa thông tin về mình (học hành, công việc, tuổi, nơi ở, chuyện riêng); chỉ tập trung vào người dùng." [gemini.py diff +23].
- **modules/llm.py system prompt**: Same clause added [llm.py:161-163].
- Both files: Example changed from "mình đang phân vân về đề án tốt nghiệp" → "mình đang phân vân không biết nên chọn hướng nào" (neutral, avoids graduation trigger) [llm.py:47 diff, gemini.py:38 diff].

#### 5c. feat: contextual-music-memory (commit e66d725, PR #3)

Major feature: music suggestions based on conversation context + memory (33 files, +1468 -88) [e66d725 commit message + diff --stat].

Key additions:
- **backend/app/memory.py** (121 lines): Conversation memory — context pair (facts + summary + music profile) from turn 2; verbatim unsummarized turns; background Gemini summary every HISTORY_TURNS + SUMMARY_BATCH_TURNS [memory.py:1-156].
- **backend/app/music_tag.py** (52 lines): Tag splitter for [NHAC:CO]/[NHAC:KHONG] [music_tag.py:1-74].
- **pipeline.py** (+80 lines): Music decision logic — chip|llm|llm_no|no_tag|safety; parallel llm∥music when goal chip; music after llm when [NHAC:CO] tag [pipeline.py:206,221-251].
- **session.py** (+116 lines): MemorySnapshot, SessionState, summary scheduling, feedback rating storage [session.py referenced via memory.py:16].
- **schemas.py** (+7 lines): MusicDecision type, SessionTurn.music_decision, SessionTurn.rating fields [schemas.py referenced via pipeline.py:21,279-280].
- **constants.py** (+11 lines): LABELS_VI, SUMMARY_BATCH_TURNS, SUMMARY_TIMEOUT [constants.py referenced via memory.py:14].
- Frontend: SongList.tsx updated, api-types.gen.ts regenerated from OpenAPI [diff --stat].

## Next reads (若 scope 对消费者不足)

- About Gemini fallback + summarize prompt internals → backend/app/gemini.py:56-120 (SUMMARY_SYSTEM_PROMPT, build_payload, summarize function).
- About session store internals (MemorySnapshot, SessionState, MAX_SESSIONS) → backend/app/session.py + backend/app/constants.py:13-15.
- About feedback route contract (rating → session → music profile) → backend/app/routes/feedback.py + backend/app/feedback.py.
- About frontend component tree (ChatView → MessageList → BotMessage → SafetyAlert, VoiceChat) → frontend/src/components/chat/ChatView.tsx, frontend/src/hooks/chat-state.ts, frontend/src/lib/api.ts.
- About audio normalization pipeline (ffmpeg, MAX_AUDIO_SECONDS, MAX_AUDIO_MB) → backend/app/audio.py.
- About CI/CD + deploy (docker, GHCR, Caddy proxy) → prior cache file .bcc-cache/20261110-115647-be125ddbcae3-produce-a-runbook-map-1-how-colab-server.md (posterior 0.97, covers full deploy runbook).
- About ML experiments (E3/E4, CafeBERT benchmark, Qwen zero-shot) → colab/experiment_E3_E4_completed.ipynb, docs/report-ML-Quyen.md.

## Gherkin scenarios (≥ 1 when applicable)

```gherkin
Feature: Pipeline safety fail-closed ordering
  Scenario: safety runs before emotion, risk=true skips emotion/llm/music
    Given a chat request with text "mình muốn làm mình đau"
    When pipeline.handle_chat processes the request
    Then safety.check_safety is called first
    And if risk=true, emotion module is NOT called
    And llm module is NOT called
    And music module is NOT called
    And reply = safety_msg, emotion=null, songs=[]
    # pipeline.py:188-210,262-265

  Scenario: safety error triggers keyword fallback (fail-closed)
    Given safety module raises NotImplementedError
    When pipeline.handle_chat processes the request
    Then fallbacks.keyword_safety(text) is called
    And if keyword_safety finds risk, reply = safety_message()
    # pipeline.py:197-201

Feature: Module registry swap mechanism
  Scenario: mock mode returns mocks.* implementation
    Given MODEL_MODE=mock (default)
    When registry.get("emotion") is called
    Then it returns mocks.emotion.predict_emotion
    # registry.py:64,76-78

  Scenario: remote mode returns model_server client for emotion/speech/llm
    Given EMOTION_MODE=remote and MODEL_SERVER_URL set
    When registry.get("emotion") is called
    Then it returns model_server.predict_emotion (httpx client)
    # registry.py:69-74

  Scenario: remote mode rejected for safety and music
    Given SAFETY_MODE=remote
    When registry.get("safety") is called
    Then RemoteNotConfigured is raised
    # registry.py:32,69-71

Feature: Context-leak fix strips [BỐI CẢNH] from LLM reply
  Scenario: LLM copies context label into reply
    Given LLM reply starts with "[BỐI CẢNH CUỘC TRÒ CHUYỆN — tóm tắt..."
    When split_music_tag processes the reply
    Then the context-label line is removed
    And the user sees only the actual reply text
    # music_tag.py:29,38-46,69

Feature: No-persona fix prevents LLM from fabricating personal life
  Scenario: Qwen tries to roleplay a person with graduation story
    Given system prompt includes "không đóng vai một người có đời sống riêng"
    And example changed from "đề án tốt nghiệp" to neutral phrasing
    When LLM generates a reply
    Then it should not claim to be graduating or working part-time
    # llm.py:161-163, gemini.py SYSTEM_PROMPT

Feature: Contextual music memory injects facts from turn 2
  Scenario: turn 2 context pair includes turn count and recent emotions
    Given session has 1 prior turn
    When memory.build_history constructs history for turn 2
    Then history[0] = {role: "user", content: "[BỐI CẢNH CUỘC TRÒ CHUYỆN — ghi chú...]\nTin nhắn sắp tới là lượt thứ 2..."}
    And history[1] = {role: "assistant", content: "Mình nhớ rồi."}
    # memory.py:82-108

  Scenario: turn 1 has no context pair
    Given session has 0 prior turns (first turn)
    When memory.build_history constructs history
    Then _context_message returns None
    And history is empty (no context pair)
    # memory.py:82-83
```
