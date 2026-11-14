# ANSWER

## TL;DR (≤ 5 行, AI 5 秒可读)

- answer: Verbatim extraction of ML-data (UIT-VSMEC, 5548/686/693, 7 labels, test distribution), ML-training (CafeBERT inference-only BATCH=64 max_length=256; fine-tune hyperparams NOT_IN_OUTPUT; Qwen3-4B greedy temp=0 max_new_tokens=8 for E4; runtime LLM temp=0.7 top_p=0.8 top_k=20 max_new_tokens=128), ML-metrics (E3 macro-F1 0.6209, per-label F1, E4 v3 0.4505, ablation v1/v2, majority 0.2667), runtime thresholds (all config.py/constants.py/audio.py values with file:line), music rules, fallback chain, feedback route contract, and explicit GAPS list.
- scope_in: [ML-DATA: dataset identity, splits, label distribution, preprocessing; ML-TRAINING: per-model train/inference steps with cell refs; ML-METRICS: full metric tables with per-label F1 + ablation; RUNTIME-FACTS: all thresholds, timeouts, batch sizes, temperature, music rules, fallback chain, feedback route; GAPS: ABSENT/NOT_IN_OUTPUT/CONFLICT items].
- scope_out: [CafeBERT fine-tune training hyperparams (epochs/lr/batch for training — not in notebook); train/val label distribution (only test in outputs); E4 v1/v2 raw reply outputs (v1 file missing, v2 only summary in comparison table); music recommend() implementation (stub NotImplementedError); safety check_safety() implementation (stub NotImplementedError); frontend runtime config; deploy/CI thresholds].
- stale_check: git_head=da1b8a7; verify with `git -C /Users/quiniu/fsb/NLP/final_project/emotion-chatbot diff HEAD -- colab/experiment_E3_E4_completed.ipynb docs/report-ML-Quyen.md backend/app/config.py backend/app/constants.py backend/app/audio.py backend/modules/llm.py backend/modules/emotion.py backend/modules/speech.py`.

## Frontmatter
created: 2026-11-13T17:03:00
question: Verbatim ML/data/runtime extraction table for writing 3 grounded docs — dataset identity, training steps, metric tables, runtime thresholds, gaps.
posterior_final: 0.97
rg_calls_used: 3
engine: opencode
git_head: da1b8a7
git_branch: view-latest-main
files_verified_mtime:
  colab/experiment_E3_E4_completed.ipynb: 2026-11-12T09:39:04
  docs/report-ML-Quyen.md: 2026-11-12T09:52:53
  backend/app/config.py: 2026-11-13T16:49:11
  backend/app/constants.py: 2026-11-13T16:49:11
  backend/app/audio.py: 2026-11-10T11:52:30
  backend/modules/llm.py: 2026-11-10T14:18:32
  backend/modules/emotion.py: 2026-11-10T14:18:32
  backend/modules/speech.py: 2026-11-10T14:18:32
  backend/app/gemini.py: 2026-11-13T16:49:11
  backend/app/fallbacks.py: 2026-11-10T11:52:30
  backend/app/feedback.py: 2026-11-10T11:52:30
  backend/app/routes/feedback.py: 2026-11-10T11:52:30
  backend/app/session.py: 2026-11-10T11:52:30
  backend/modules/music.py: 2026-11-10T14:18:32
  backend/modules/safety.py: 2026-11-10T11:52:30
  colab/README.md: 2026-11-10T11:52:30

## Spec (formal-spec; PRE / POST / INV / ERR / KILL when applicable)

PRE: Repo @ da1b8a7, branch view-latest-main. Sources whitelisted: colab/experiment_E3_E4_completed.ipynb (cells 0-13, with outputs), colab/README.md, docs/report-ML-Quyen.md, backend/app/{config,constants,audio,session,feedback,gemini,fallbacks,memory,music_tag,pipeline,registry}.py, backend/app/routes/{chat,feedback}.py, backend/modules/{emotion,speech,llm,music,safety}.py.
POST: ∀ claim ∈ Findings: cited with file:line. ∀ number: verbatim, not paraphrased. ∀ absent-why: marked ABSENT. ∀ missing-output: marked NOT_IN_OUTPUT.
INV1: Dataset name = "UIT-VSMEC", HF id = "ura-hcmut/UIT-VSMEC" [notebook cell 3 src, cell 3 output].
INV2: 7 labels alphabetical = ["Anger","Disgust","Enjoyment","Fear","Other","Sadness","Surprise"] [constants.py:3].
INV3: Splits = train 5548 / validation 686 / test 693 [notebook cell 3 output].
INV4: E3 macro-F1 = 0.6209 ∈ [0.620, 0.634] → "đạt" target [report-ML-Quyen.md:32, notebook cell 8 output].
INV5: Fine-tune hyperparams (epochs, lr, training batch_size) ∉ notebook outputs → NOT_IN_OUTPUT.
ERR: Conflicting numbers report vs notebook → none found (all match).

## File map (scored + relationships)

### Scored files.

| rank | score | file | role | evidence (file:line) |
|------|-------|------|------|----------------------|
| 1 | 0.99 | colab/experiment_E3_E4_completed.ipynb | E3/E4 experiments: dataset load, inference, metrics, ablation — all with outputs | cell 3 (splits), cell 7 (test dist), cell 8 (E3 metrics), cell 9 (per-label F1), cell 12 (E4 v3), cell 13 (comparison) |
| 2 | 0.98 | docs/report-ML-Quyen.md | ML report: 3 module table, E3/E4 analysis, model ids, metric tables, conclusions | report-ML-Quyen.md:10-14,27-53 |
| 3 | 0.97 | backend/app/config.py | All runtime thresholds: audio limits, timeouts, history/summary settings, remote timeouts | config.py:31-53 |
| 4 | 0.95 | backend/app/constants.py | Label list, goals, module names, modes, max sessions/turns/message | constants.py:3-29 |
| 5 | 0.93 | backend/modules/llm.py | LLM generation hyperparams, music tag rules, model ids, safe reply | llm.py:22,25,30,34-52,221-225 |
| 6 | 0.92 | backend/modules/emotion.py | CafeBERT predict_emotion: model id, tokenizer use_fast=False, max_length=256, device chain | emotion.py:19,47,122 |
| 7 | 0.90 | backend/modules/speech.py | PhoWhisper model id, prosody thresholds (energy 0.02/0.08, pitch 250Hz), pitch fmin/fmax | speech.py:17,100-105,80-82 |
| 8 | 0.88 | backend/app/audio.py | Audio normalization: FFMPEG_TIMEOUT, CHUNK_BYTES, READ_MARGIN, DURATION_TOLERANCE, ffmpeg args | audio.py:20-25,116-154 |
| 9 | 0.85 | backend/app/gemini.py | Gemini generate/summarize config: temperature 0.8/0.3, maxOutputTokens 1024, model id | gemini.py:26,124,189 |
| 10 | 0.82 | backend/app/fallbacks.py | Fallback chain: canned replies per label, keyword_safety risk phrases, safety_message | fallbacks.py:8-28,30-42,54-84 |
| 11 | 0.80 | backend/app/routes/feedback.py | Feedback route contract: POST /api/feedback, GET /api/feedback/export | feedback.py routes:16-57 |
| 12 | 0.78 | backend/app/feedback.py | Feedback save: JSONL append, FIELDS list, CSV export with injection guard | feedback.py:11-21,52-55,74-79 |
| 13 | 0.75 | backend/app/session.py | Session store: SessionState, MemorySnapshot, MAX_SESSIONS/MAX_SESSION_TURNS, LRU eviction | session.py:11-29,42-55 |
| 14 | 0.70 | colab/README.md | Model server Colab runbook: HTTP contract, model ids, mode constraints | colab/README.md:3,13-15,19-29 |
| 15 | 0.65 | backend/modules/music.py | Music recommend stub: NotImplementedError("Người 5 phụ trách") | music.py:7,15 |
| 16 | 0.60 | backend/modules/safety.py | Safety stub: NotImplementedError("Người 3 phụ trách") | safety.py:7,14 |

### Relationships (formal-spec).

CONTRACTS:
  - F := scored_files.
  - rel: F × F × KIND → bool. KIND ∈ { imports, calls, inherits, configures, tests, references, defines, triggered_by, depends_on }.

EDGES:
  rel(backend/app/routes/feedback.py, backend/app/feedback.py, calls) ⇒ feedback.py routes:8,23
  rel(backend/app/routes/feedback.py, backend/app/session.py, calls) ⇒ feedback.py routes:11,18
  rel(backend/app/feedback.py, backend/app/config.py, depends_on) ⇒ feedback.py:9,27
  rel(backend/app/session.py, backend/app/constants.py, depends_on) ⇒ session.py:7
  rel(backend/modules/llm.py, backend/app/constants.py, references) ⇒ llm.py:65-70 (_LABELS_VI mirrors constants.py:6-14)
  rel(backend/modules/emotion.py, backend/app/constants.py, references) ⇒ emotion.py:19 (LABELS from constants)
  rel(backend/app/gemini.py, backend/app/config.py, depends_on) ⇒ gemini.py:10,143
  rel(backend/app/gemini.py, backend/app/constants.py, references) ⇒ gemini.py:11 (LABELS_VI)
  rel(backend/app/audio.py, backend/app/config.py, depends_on) ⇒ audio.py:16
  rel(colab/experiment_E3_E4_completed.ipynb, backend/modules/emotion.py, references) ⇒ notebook cell 7 (MODEL_NAME = "BaoNyan/cafebert-UITVSMEC" = emotion.py:19)
  rel(docs/report-ML-Quyen.md, colab/experiment_E3_E4_completed.ipynb, references) ⇒ report-ML-Quyen.md:4 (all numbers from notebook)
  rel(colab/README.md, backend/modules/emotion.py, references) ⇒ colab/README.md:13 (CafeBERT id)
  rel(colab/README.md, backend/modules/speech.py, references) ⇒ colab/README.md:14 (PhoWhisper)

### Topology.

  - entry_point := colab/experiment_E3_E4_completed.ipynb cell 3 (dataset load) → cell 7 (E3 inference) → cell 12 (E4 inference) → cell 13 (comparison table).
  - critical_path := notebook cell 3 (load_dataset) → cell 5 (detect_cols + label map) → cell 7 (load CafeBERT + id2label) → cell 8 (batch inference + metrics) → cell 9 (per-label F1 + confusion) → cell 11 (load Qwen3-4B) → cell 12 (greedy classify + metrics) → cell 13 (comparison table).
  - leaf_files := { backend/app/config.py, backend/app/constants.py, backend/modules/music.py, backend/modules/safety.py, colab/README.md }.

## Behavior (input → process → output, 运行时视图)

- input: HF dataset `ura-hcmut/UIT-VSMEC` loaded via `datasets.load_dataset("ura-hcmut/UIT-VSMEC")` [notebook cell 3 src]. Features: `['Emotion', 'Sentence']` [notebook cell 3 output]. Splits: train 5548, validation 686, test 693 [notebook cell 3 output]. Pre-trained model checkpoint `BaoNhan/cafebert-UITVSMEC` from HF [notebook cell 7 src, emotion.py:19]. Qwen3-4B checkpoint `Qwen/Qwen3-4B` from HF [notebook cell 11 src, llm.py:10].
- process:
  (1) Column detection: `detect_cols(test_ds)` auto-maps `Sentence`→TEXT_COL, `Emotion`→LAB_COL by value inspection [notebook cell 5 src+output].
  (2) Label normalization: lowercase dataset values mapped to 7 standard labels alphabetically [notebook cell 5 output: `{'sadness':'Sadness',...}`].
  (3) E3 CafeBERT inference: `AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)`, `AutoModelForSequenceClassification.from_pretrained(MODEL_NAME).eval().cuda()` [notebook cell 7 src]. Batch inference `BATCH=64`, `max_length=256`, `truncation=True`, `padding=True`, `.to("cuda")` [notebook cell 8 src].
  (4) E3 metrics: `accuracy_score`, `f1_score(average='macro')`, `f1_score(average='weighted')`, `classification_report` [notebook cell 8 src+output].
  (5) E4 v3 Qwen3-4B: `N_E4=150, SEED=42`, `random.seed(SEED)`, `random.sample(range(len(texts)), 150)` [notebook cell 11 src]. Greedy decode: `do_sample=False, max_new_tokens=8` [notebook cell 10 markdown, notebook experiment_E3_E4.ipynb:304]. `enable_thinking=False` via chat template [notebook cell 12 src].
  (6) E4 metrics: parse reply → label via VERBALIZERS dict, `accuracy_score`, `f1_score` [notebook cell 12 src+output].
  (7) Comparison: E3 vs v2 vs v3 vs majority-baseline in DataFrame [notebook cell 13 src+output].
- output: E3 results: `{'accuracy': 0.6681, 'macro_f1': 0.6209, 'weighted_f1': 0.6636}` saved to `/content/E3_results.json` [notebook cell 8 output]. E4 v3 results: `accuracy=0.5133, macro-F1=0.4505, weighted-F1=0.4763` saved to `E4_v3_results.json` + `E4_v3_replies.json` [notebook cell 12 output]. Confusion matrix PNG: `/content/E3_confusion.png` [notebook cell 9 output]. Comparison table [notebook cell 13 output].
- side_effects: HF dataset download (network); HF model downloads (network); PNG file writes (`/content/E3_confusion.png`); JSON file writes (`/content/E3_results.json`, `E4_v3_results.json`, `E4_v3_replies.json`); Colab GPU T4 usage.

## Findings (cite file:line)

### (1) ML-DATA: Dataset Identity, Origin, Label Distribution, Splits, Preprocessing

| Field | Value | Source |
|-------|-------|--------|
| Dataset name | UIT-VSMEC | notebook cell 3 src; report-ML-Quyen.md:27 |
| HF id | `ura-hcmut/UIT-VSMEC` | notebook cell 3 src |
| Features | `['Emotion', 'Sentence']` | notebook cell 3 output |
| Text column | `Sentence` | notebook cell 5 output |
| Label column | `Emotion` | notebook cell 5 output |
| Num labels | 7 | constants.py:3; notebook cell 7 output (`cfg.num_labels == 7`) |
| Labels (alphabetical) | Anger, Disgust, Enjoyment, Fear, Other, Sadness, Surprise | constants.py:3; notebook cell 5 src |
| Label map | `{sadness→Sadness, surprise→Surprise, disgust→Disgust, fear→Fear, anger→Anger, other→Other, enjoyment→Enjoyment}` | notebook cell 5 output |
| Train split | 5548 rows | notebook cell 3 output |
| Validation split | 686 rows | notebook cell 3 output |
| Test split | 693 rows | notebook cell 3 output |
| Test label dist | Enjoyment=193, Disgust=132, Other=129, Sadness=116, Fear=46, Anger=40, Surprise=37 | notebook cell 7 output |
| Train label dist | NOT_IN_OUTPUT | — |
| Val label dist | NOT_IN_OUTPUT | — |
| Vietnamese preprocessing | None explicit; text used as-is; CafeBERT tokenizer `use_fast=False` (sentencepiece.bpe.model only, no tokenizer.json) | emotion.py:47; report-ML-Quyen.md:20 |
| WHY dataset chosen | ABSENT | — (not stated in notebook or report) |

**Paper reference**: UIT-VSMEC baseline CNN ~57.6% F1 (PACLING 2019) [report-ML-Quyen.md:51]. ViSoBERT ~66% F1 [report-ML-Quyen.md:52].

### (2) ML-TRAINING: Per-Model Train Steps

#### CafeBERT (emotion module)

| Item | Value | Source |
|------|-------|--------|
| Model id | `BaoNhan/cafebert-UITVSMEC` | notebook cell 7 src; emotion.py:19; report-ML-Quyen.md:12 |
| id2label | `{0:'Anger', 1:'Disgust', 2:'Enjoyment', 3:'Fear', 4:'Other', 5:'Sadness', 6:'Surprise'}` | notebook cell 7 output |
| Tokenizer | `AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)` | notebook cell 7 src; emotion.py:47 |
| Inference batch | `BATCH = 64` | notebook cell 8 src |
| Max length | `max_length=256`, `truncation=True`, `padding=True` | notebook cell 8 src; emotion.py:122 |
| Device | `.eval().cuda()` (T4) | notebook cell 7 src |
| Fine-tune epochs | NOT_IN_OUTPUT (notebook loads pre-trained checkpoint, no training cells) | — |
| Fine-tune learning rate | NOT_IN_OUTPUT | — |
| Fine-tune batch size (training) | NOT_IN_OUTPUT | — |
| Runtime device chain | cuda > mps > cpu | emotion.py:49-54; report-ML-Quyen.md:19 |

#### PhoWhisper (speech module)

| Item | Value | Source |
|------|-------|--------|
| Model id | `vinai/PhoWhisper-base` | speech.py:17; report-ML-Quyen.md:13 |
| Pipeline | `pipeline("automatic-speech-recognition", model=_ASR_MODEL_NAME)` | speech.py:31-34 |
| Input format | WAV 16 kHz mono (normalized by audio.py) | speech.py:7-8; audio.py:128 |
| Training | NOT_IN_OUTPUT (pre-trained, no fine-tune) | — |

#### Qwen LLM (llm module)

| Item | Value | Source |
|------|-------|--------|
| Default model (local) | `Qwen/Qwen2.5-3B-Instruct` | llm.py:22; report-ML-Quyen.md:14 |
| Colab model | `Qwen/Qwen3-4B` via env `LLM_MODEL_ID` | llm.py:10; report-ML-Quyen.md:14 |
| Runtime generation | `max_new_tokens=128, do_sample=True, temperature=0.7, top_p=0.8, top_k=20` | llm.py:221-225 |
| enable_thinking | `False` (with TypeError fallback for Qwen2.5 template) | llm.py:208-213; report-ML-Quyen.md:21 |
| Safe reply | `"Mình ở đây, bạn yên tâm kể mình nghe nha."` | llm.py:25 |
| Max history messages | 40 | llm.py:30 |

#### E4 Experiment (Qwen3-4B zero-shot)

| Item | Value | Source |
|------|-------|--------|
| Model | `Qwen/Qwen3-4B` | notebook cell 11 src+output |
| N samples | 150 | notebook cell 11 src (`N_E4 = 150`) |
| Seed | 42 | notebook cell 11 src (`SEED = 42`) |
| Sampling | `random.seed(SEED)`, `random.sample(range(len(texts)), 150)` | notebook cell 11 src |
| Decoding | greedy: `do_sample=False, max_new_tokens=8` (temperature=0) | notebook cell 10 markdown; colab/experiment_E3_E4.ipynb:304 |
| enable_thinking | `False` via chat template (with TypeError fallback) | notebook cell 12 src |
| Verbalizer | VI+EN dict (e.g. `"Anger": ["Anger","Giận","Tức giận"]`) | notebook cell 11 src |

#### Prosody (speech module, no model)

| Item | Value | Source |
|------|-------|--------|
| Tool | librosa (no SER model — heuristic) | speech.py:9-11; report-ML-Quyen.md:13 |
| Pitch | `librosa.pyin(fmin=70, fmax=400, frame_length=2048)` | speech.py:80-82 |
| Max pitch length | 30s * sr (matches MAX_AUDIO_SECONDS) | speech.py:78 |
| Arousal low | `energy_rms < 0.02` | speech.py:102 |
| Arousal high | `energy_rms > 0.08 OR (pitch_mean > 250.0 AND energy_rms > 0.04)` | speech.py:100-101 |
| Arousal medium | else | speech.py:104-105 |

### (3) ML-METRICS: Full Metric Tables

#### E3 — CafeBERT fine-tuned on UIT-VSMEC test (n=693)

| Metric | Value | Target | Source |
|--------|-------|--------|--------|
| accuracy | 0.6681 | — | notebook cell 8 output; report-ML-Quyen.md:31 |
| macro-F1 | 0.6209 | 0.627 ± 0.007 → đạt (0.6209 ∈ [0.620, 0.634]) | notebook cell 8 output; report-ML-Quyen.md:32 |
| weighted-F1 | 0.6636 | — | notebook cell 8 output; report-ML-Quyen.md:33 |

**Per-label classification report (verbatim from notebook cell 8 output):**

| Label | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| Anger | 0.452 | 0.350 | 0.394 | 40 |
| Disgust | 0.597 | 0.674 | 0.633 | 132 |
| Enjoyment | 0.737 | 0.798 | 0.766 | 193 |
| Fear | 0.652 | 0.652 | 0.652 | 46 |
| Other | 0.626 | 0.519 | 0.568 | 129 |
| Sadness | 0.754 | 0.767 | 0.761 | 116 |
| Surprise | 0.606 | 0.541 | 0.571 | 37 |
| **accuracy** | | | **0.668** | **693** |
| **macro avg** | 0.632 | 0.615 | 0.621 | 693 |
| **weighted avg** | 0.664 | 0.668 | 0.664 | 693 |

Source: notebook cell 8 output (classification_report printed verbatim); notebook cell 9 output (F1 dict: `{'Anger': 0.394, 'Disgust': 0.633, 'Enjoyment': 0.766, 'Fear': 0.652, 'Other': 0.568, 'Sadness': 0.761, 'Surprise': 0.571}`).

#### E4 — Qwen3-4B zero-shot ablation (n=150, seed=42)

| Protocol | accuracy | macro-F1 | weighted-F1 | n | Source |
|----------|----------|----------|-------------|---|--------|
| v1 — server `/generate`, sampling 0.7, nhãn EN | 0.2267 | 0.0588 | — | 150 | notebook cell 10 markdown; cell 13 output |
| v2 — server `/generate`, parse VI+EN (confound persona) | 0.2333 | 0.0657 | 0.1056 | 150 | notebook cell 13 output |
| **v3 — raw Qwen local, greedy (temp=0), verbalizer VI+EN** | **0.5133** | **0.4505** | **0.4763** | 150 | notebook cell 12 output; cell 13 output |
| Majority-baseline (always-Enjoyment) | 0.2667 | NaN | NaN | 150 | notebook cell 13 output |

**E4 v3 prediction distribution (verbatim):** `Counter({'Sadness': 52, 'Other': 39, 'Enjoyment': 34, 'Anger': 11, 'Fear': 6, 'Surprise': 4, 'Disgust': 4})` [notebook cell 12 output].
**E4 v3 parse stats:** `{'parse_ok': 150, 'fallback_other': 0, 'n': 150}` [notebook cell 12 output].

**Ablation notes (verbatim from notebook cell 10 markdown):**
- v1: "toàn fallback → parse-fail"
- v2: "**confound**: endpoint bọc system-prompt chatbot ('Hệ thống phát hiện cảm xúc: Other') → model bị chi phối nhãn ngữ cảnh" — "148/150 = 'Other'"
- v3: "chuẩn evaluation: deterministic, không wrapper"

**External baselines (from report):**

| Reference | F1 | Source |
|-----------|-----|--------|
| UIT-VSMEC CNN baseline (PACLING 2019) | ~57.6% | report-ML-Quyen.md:51 |
| ViSoBERT fine-tuned (same dataset) | ~66% | report-ML-Quyen.md:52 |
| CafeBERT (this work) | 0.6681 acc / 0.6209 macro-F1 | report-ML-Quyen.md:51 |
| E4 Qwen zero-shot | ~0.45 (±0.05, n=150) | report-ML-Quyen.md:53 |

**Notebook cell 13 output (verbatim comparison table):**
```
                                               Bản  accuracy  macro-F1  weighted-F1   n
                            E3 CafeBERT fine-tuned    0.6681    0.6209       0.6636 693
v2 server+sampling, parse VI+EN (confound persona)    0.2333    0.0657       0.1056 150
                           v3 raw + greedy (chuẩn)    0.5133    0.4505       0.4763 150
              Majority-baseline (always-Enjoyment)    0.2667       NaN          NaN 150
```

### (4) RUNTIME-FACTS: Thresholds, Timeouts, Batch Sizes, Music Rules, Fallback Chain, Feedback Route

#### Audio thresholds (config.py + audio.py)

| Parameter | Value | Source |
|-----------|-------|--------|
| MAX_AUDIO_SECONDS | 30 | config.py:31 |
| MAX_AUDIO_MB | 5 | config.py:32 |
| FFMPEG_BINARY | "ffmpeg" | config.py:33 |
| FFMPEG_TIMEOUT_S | 15 | audio.py:20 |
| CHUNK_BYTES | 64 * 1024 (65536) | audio.py:21 |
| READ_MARGIN_S | 1.5 | audio.py:23 |
| DURATION_TOLERANCE_S | 1.0 | audio.py:25 |
| ffmpeg output format | WAV 16kHz mono s16 (`-ar 16000 -ac 1 -sample_fmt s16`) | audio.py:128 |
| ffmpeg clip limit | `-t {max_s + READ_MARGIN_S}` = 31.5s | audio.py:127 |

#### Session & memory thresholds (config.py + constants.py)

| Parameter | Value | Source |
|-----------|-------|--------|
| HISTORY_TURNS | 6 | config.py:34 |
| SUMMARY_BATCH_TURNS | 4 | config.py:35 |
| SUMMARY_MAX_WORDS | 120 | config.py:36 |
| MAX_SESSIONS | 1000 | constants.py:29; session.py:42 |
| MAX_SESSION_TURNS | 200 | constants.py:28; session.py:42 |
| MAX_MESSAGE_CHARS | 1000 | constants.py:27 |
| Memory cap (no Gemini key) | HISTORY_TURNS + 2 * SUMMARY_BATCH_TURNS = 14 | memory.py:95 |
| Summary trigger | unsummarized >= HISTORY_TURNS + SUMMARY_BATCH_TURNS = 10 | memory.py:122 |
| Max history messages (LLM) | 40 | llm.py:30 |

#### Module timeouts (config.py)

| Parameter | Value (seconds) | Source |
|-----------|-----------------|--------|
| SAFETY_TIMEOUT | 5.0 | config.py:39 |
| EMOTION_TIMEOUT | 10.0 | config.py:40 |
| LLM_TIMEOUT | 30.0 | config.py:41 |
| MUSIC_TIMEOUT | 5.0 | config.py:42 |
| SPEECH_TIMEOUT | 20.0 | config.py:43 |
| PROSODY_TIMEOUT | 10.0 | config.py:44 |
| GEMINI_TIMEOUT | 20.0 | config.py:45 |
| SUMMARY_TIMEOUT | 20.0 | config.py:46 |
| REMOTE_TIMEOUT_EMOTION | 10.0 | config.py:49 |
| REMOTE_TIMEOUT_TRANSCRIBE | 20.0 | config.py:50 |
| REMOTE_TIMEOUT_PROSODY | 10.0 | config.py:51 |
| REMOTE_TIMEOUT_GENERATE | 30.0 | config.py:52 |
| REMOTE_TIMEOUT_HEALTH | 3.0 | config.py:53 |

#### Generation hyperparams

| Engine | temperature | max tokens | top_p | top_k | do_sample | Source |
|--------|-------------|------------|-------|-------|-----------|--------|
| Qwen (runtime llm.py) | 0.7 | max_new_tokens=128 | 0.8 | 20 | True | llm.py:221-225 |
| Qwen (E4 v3 notebook) | 0 (greedy) | max_new_tokens=8 | — | — | False | notebook cell 10; experiment_E3_E4.ipynb:304 |
| Gemini generate | 0.8 | maxOutputTokens=1024 | — | — | — | gemini.py:124 |
| Gemini summarize | 0.3 | maxOutputTokens=1024 | — | — | — | gemini.py:189 |

#### Model IDs

| Module | Model id | Source |
|--------|----------|--------|
| Emotion | `BaoNhan/cafebert-UITVSMEC` | emotion.py:19 |
| Speech (ASR) | `vinai/PhoWhisper-base` | speech.py:17 |
| LLM (local default) | `Qwen/Qwen2.5-3B-Instruct` | llm.py:22 |
| LLM (Colab, env LLM_MODEL_ID) | `Qwen/Qwen3-4B` | llm.py:10 |
| Gemini | `gemini-3.5-flash-lite` (default, config GEMINI_MODEL) | config.py:26 |

#### Music rules (verbatim from llm.py:34-52)

```
Dòng đầu tiên của câu trả lời bắt buộc là [NHAC:CO] hoặc [NHAC:KHONG],
sau đó xuống dòng rồi mới trả lời.
Chọn [NHAC:CO] chỉ khi:
(1) người dùng xin nghe nhạc, hỏi bài hát hoặc nhờ gợi ý bài; hoặc
(2) người dùng đã buồn, lo sợ hoặc tức giận rõ rệt ở ít nhất 2 lượt gần đây
    (tính cả lượt hiện tại) và lượt ngay trước chưa được gợi ý nhạc.
Mọi trường hợp khác chọn [NHAC:KHONG], nhất là: lượt đầu tiên; lần đầu kể một chuyện
(hãy lắng nghe trước); cảm xúc Bình thường hoặc Vui vẻ; chào hỏi, cảm ơn, hỏi thông tin;
người dùng đã nói không muốn nghe nhạc.
Ví dụ:
"chào bạn" → [NHAC:KHONG]
"mình đang phân vân không biết nên chọn hướng nào" → [NHAC:KHONG]
"có bài nào nghe cho vui không" → [NHAC:CO]
lượt thứ 3, hai lượt trước đều buồn: "mình sợ rớt môn lắm, chán ghê" → [NHAC:CO]
Không nhắc tới thẻ này hay tự liệt kê bài hát trong câu trả lời.
```

Source: llm.py:34-52 (mirrored in gemini.py:26-40). Tag splitting: music_tag.py:49-74 (`split_music_tag` strips `[NHAC:CO]`/`[NHAC:KHONG]` + `[BỐI CẢNH]` lines).

Music module `recommend(label, arousal, goal, k=5)` → **NotImplementedError** stub ("Người 5 phụ trách") [music.py:7,15]. Mock reads `data/songs.csv` [mocks/music.py:13,21]. Mode ∈ {mock, local} only (NOT remote) [registry.py:32,69-71].

#### Fallback chain (pipeline.py)

| Step | Trigger | Fallback | Source |
|------|---------|----------|--------|
| Safety error/timeout | try_call(safety) fails | `keyword_safety(text)` — Vietnamese risk phrases (stripped accents match) | pipeline.py:197-201; fallbacks.py:30-42,64-70 |
| Safety risk=true | keyword_safety returns True | `safety_message()` — canned safety msg + optional hotline | pipeline.py:209-210; fallbacks.py:73-84 |
| Emotion error/timeout | try_call(emotion) fails | `fallback_emotion()` → label="Other", uniform probs | pipeline.py:213-219; fallbacks.py:54-57 |
| LLM error | registry.get("llm") fails | Gemini generate_reply (if GEMINI_API_KEY + not already gemini mode) | pipeline.py:76-127 |
| Gemini error/fallback | Gemini fails or no API key | `canned_reply(label)` — per-label canned Vietnamese response | pipeline.py:127; fallbacks.py:8-28,60-61 |
| Speech transcribe error | transcribe() raises | empty string "" | speech.py:52-53 |
| LLM empty reply | reply is empty string | `"Mình nghe bạn rồi, muốn kể thêm không nè?"` | llm.py:232 |

**Safety risk phrases (verbatim from fallbacks.py:30-42):**
`tự tử, tự sát, muốn chết, không muốn sống, không muốn tồn tại, tự làm hại, tự hại bản thân, cắt tay, kết liễu, kết thúc cuộc đời, chết đi cho rồi`

#### Feedback route contract

| Route | Method | Input | Output | Auth | Source |
|-------|--------|-------|--------|------|--------|
| `/api/feedback` | POST | `FeedbackRequest{session_id, turn_id, rating}` | `FeedbackResponse` (empty) | none | routes/feedback.py:16-36 |
| `/api/feedback/export` | GET | — | CSV attachment (`feedback.csv`, `text/csv; charset=utf-8`) | Bearer ADMIN_TOKEN | routes/feedback.py:39-57 |

**POST /api/feedback behavior:**
1. Look up turn by `turn_id` in session store → 404 if not found [routes/feedback.py:18-21]
2. `store.set_rating(session_id, turn_id, rating)` [routes/feedback.py:22]
3. `feedback.save(record)` — appends JSONL line with fields: `session_id, turn_id, rating, emotion_label, arousal, goal, safety, llm_backend, created_at` [routes/feedback.py:23-35; feedback.py:11-21,52-55]
4. No message content or reply text saved [feedback.py:1]

**GET /api/feedback/export behavior:**
1. Check `ADMIN_TOKEN` config → 404 if not set [routes/feedback.py:41-43]
2. Validate `Authorization: Bearer <token>` → 401 if mismatch [routes/feedback.py:44-52]
3. `feedback.export_csv()` — deduplicates by turn_id (latest wins), CSV injection guard on cells starting with `=+-@\t\r` [feedback.py:58-64,67-79]
4. Returns CSV with header row = FIELDS [feedback.py:77]

**Feedback file path:** `FEEDBACK_PATH = "data/runtime/feedback.jsonl"` [config.py:28]

### (5) GAPS: ABSENT / NOT_IN_OUTPUT / CONFLICT Items

| Item | Status | Detail |
|------|--------|--------|
| WHY UIT-VSMEC dataset chosen | ABSENT | Not stated in notebook or report — no explicit rationale for dataset selection |
| CafeBERT fine-tune epochs | NOT_IN_OUTPUT | Notebook loads pre-trained checkpoint `BaoNyan/cafebert-UITVSMEC`; no training cells; no epoch value in any output |
| CafeBERT fine-tune learning rate | NOT_IN_OUTPUT | Same — no lr in outputs |
| CafeBERT fine-tune training batch size | NOT_IN_OUTPUT | Only inference BATCH=64 is in notebook; training batch not in outputs |
| Train split label distribution | NOT_IN_OUTPUT | Only test split distribution in notebook cell 7 output (193/132/129/116/46/40/37); train/val distributions not printed |
| Validation split label distribution | NOT_IN_OUTPUT | Same as above |
| E4 v1 raw reply outputs | NOT_IN_OUTPUT | Notebook cell 13 prints "(Khong co file E4_v1 — dung so v1 lich su 0.2267/0.0588 vao bang bao cao)"; v1 numbers are historical, not from current run |
| E4 v2 raw reply outputs | NOT_IN_OUTPUT | Only summary metrics in comparison table (0.2333/0.0657/0.1056); raw replies not in current notebook outputs |
| Music recommend() implementation | STUB | `raise NotImplementedError("Người 5 phụ trách: recommend")` [music.py:15] — only mock implementation exists [mocks/music.py:21] |
| Safety check_safety() implementation | STUB | `raise NotImplementedError("Người 3 phụ trách")` [safety.py:14] — only keyword_safety fallback exists [fallbacks.py:64-70] |
| Conflicts report vs notebook | NONE | All numbers match between report-ML-Quyen.md and notebook outputs (verified: E3 0.6681/0.6209/0.6636, E4 v3 0.5133/0.4505/0.4763, majority 0.2667, v1 0.2267/0.0588, v2 0.2333/0.0657) |
| PhoWhisper model size discrepancy | CONFLICT | colab/README.md:14 says `vinai/PhoWhisper-small`; speech.py:17 and report-ML-Quyen.md:13 say `vinai/PhoWhisper-base`. README is for reference_modules (quick_test), production uses `PhoWhisper-base`. |
| GEMINI_MODEL id | NOT_IN_OUTPUT | config default `gemini-3.5-flash-lite` [config.py:26] — this appears to be a placeholder; no evidence of actual Gemini model used in production outputs |

## Next reads (若 scope 对消费者不足)

- About CafeBERT fine-tune training details (epochs, lr, batch) → check HF model card `https://huggingface.co/BaoNhan/cafebert-UITVSMEC` (external, not in repo).
- About train/val label distribution → run `datasets.load_dataset("ura-hcmut/UIT-VSMEC")` and count (external; notebook only printed test distribution).
- About E4 v1/v2 raw replies → `colab/experiment_E3_E4.ipynb` (pre-completed version, may contain v1/v2 outputs — current completed notebook says v1 file missing).
- About music recommend() real implementation → assignee "Người 5" [music.py:15]; no implementation in repo.
- About safety check_safety() real implementation → assignee "Người 3" [safety.py:14]; no implementation in repo.
- About Gemini model actually used → check `.env` or GitHub Environments secrets (not in repo; config default `gemini-3.5-flash-lite` may be placeholder).
- About frontend runtime config → `frontend/src/lib/api.ts`, `frontend/src/hooks/useChat.ts`.

## Gherkin scenarios (≥ 1 when applicable)

```gherkin
Feature: Verbatim ML metric extraction for grounded docs
  Scenario: E3 CafeBERT metrics match across sources
    Given notebook cell 8 output shows accuracy=0.6681, macro-F1=0.6209, weighted-F1=0.6636
    And report-ML-Quyen.md:31-33 shows the same numbers
    When extracting ML-METRICS section
    Then all three numbers are cited verbatim from both sources
    And no conflict is recorded
    # notebook cell 8 output; report-ML-Quyen.md:31-33

  Scenario: E4 ablation values extracted with protocol context
    Given notebook cell 10 markdown describes v1/v2/v3 protocols
    And notebook cell 13 output shows comparison table
    When extracting ablation table
    Then v1=0.2267/0.0588, v2=0.2333/0.0657/0.1056, v3=0.5133/0.4505/0.4763
    And v1 marked "historical, file missing" (NOT_IN_OUTPUT for raw replies)
    And majority-baseline=0.2667
    # notebook cell 10, cell 13 output

  Scenario: CafeBERT fine-tune hyperparams absent
    Given notebook only contains inference cells (load checkpoint + batch predict)
    And no training cell with epochs/lr/training-batch exists
    When extracting ML-TRAINING section
    Then epochs=NOT_IN_OUTPUT, lr=NOT_IN_OUTPUT, training_batch=NOT_IN_OUTPUT
    # notebook cells 7-8

  Scenario: Runtime thresholds extracted with file:line
    Given config.py:31 MAX_AUDIO_SECONDS=30
    And config.py:34 HISTORY_TURNS=6
    And constants.py:29 MAX_SESSIONS=1000
    When extracting RUNTIME-FACTS
    Then each threshold cited with exact file:line
    And no value paraphrased
    # config.py:31-53, constants.py:27-29

  Scenario: Music rules extracted verbatim
    Given llm.py:34-52 contains _MUSIC_TAG_RULES string
    And gemini.py:26-40 mirrors the same rules
    When extracting music rules
    Then rules quoted verbatim with source citation
    # llm.py:34-52, gemini.py:26-40

  Scenario: Feedback route contract extracted
    Given routes/feedback.py:16-36 defines POST /api/feedback
    And routes/feedback.py:39-57 defines GET /api/feedback/export
    And feedback.py:11-21 defines FIELDS list
    When extracting feedback contract
    Then route, input, output, auth, saved fields all cited
    # routes/feedback.py:16-57, feedback.py:11-21
```
