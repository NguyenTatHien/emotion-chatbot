# ANSWER

## TL;DR (≤ 5 行, AI 5 秒可读)

- answer: Colab model server = `colab/server_app.py` (FastAPI, uvicorn `:8001`) loads `backend/{modules,mocks}/{emotion,speech,llm}` dynamically and exposes `GET /health` + `POST /emotion|/transcribe|/prosody|/generate` (token-gated via `X-Model-Server-Token`); local dev = `docker compose -f docker-compose.dev.yml up` (backend uvicorn `:8000` reload + frontend Vite `:5173`, env from `backend/.env`, defaults `MODEL_MODE=mock`); prod = GHCR images via `images.yml` → `deploy.yml` SSH → `remote-deploy.sh` runs `docker-compose.prod.yml` on `realestate-vm` behind `javis-proxy`; `requirements.txt` = light runtime (fastapi/uvicorn/pydantic/httpx), `requirements-ml.txt` = torch/transformers/librosa (lazy, `local` mode only).
- scope_in: [colab server startup + endpoints + contracts; dev compose (backend+frontend); prod compose + deploy scripts; CI/deploy/images workflows; requirements split; backend config/env defaults; registry mode resolution; Dockerfile targets; Caddy proxy].
- scope_out: [module ML internals (CafeBERT/PhoWhisper/Qwen3 weights, fp16 code); chat `/api/chat` full request/response schema fields; session store backend; feedback CSV export internals; ngrok static-domain setup steps; Gemini fallback flow detail; frontend component tree].
- stale_check: git_head=ceb62f9; verify with `git -C /Users/quiniu/fsb/NLP/final_project/emotion-chatbot diff HEAD -- colab/server_app.py docker-compose.dev.yml backend/.env.example deploy/docker-compose.prod.yml .github/workflows/ci.yml .github/workflows/deploy.yml .github/workflows/images.yml backend/requirements.txt backend/requirements-ml.txt`.

## Frontmatter
created: 2026-11-10T11:56:47
question: Runbook map — Colab model server startup/endpoints/contracts, docker dev+prod, deploy scripts, GitHub workflows, requirements split.
posterior_final: 0.97
rg_calls_used: 3
engine: opencode
git_head: ceb62f9
git_branch: main
files_verified_mtime:
  colab/server_app.py: 2026-11-10T11:52:30
  colab/requirements.txt: 2026-11-10T11:52:30
  colab/README.md: 2026-11-10T11:52:30
  docker-compose.dev.yml: 2026-11-10T11:52:30
  docker-compose.yml: 2026-11-10T11:52:30
  backend/.env.example: 2026-11-10T11:52:30
  backend/Dockerfile: 2026-11-10T11:52:30
  backend/requirements.txt: 2026-11-10T11:52:30
  backend/requirements-ml.txt: 2026-11-10T11:52:30
  backend/requirements-dev.txt: 2026-11-10T11:52:30
  backend/app/main.py: 2026-11-10T11:52:30
  backend/app/config.py: 2026-11-10T11:52:30
  backend/app/constants.py: 2026-11-10T11:52:30
  backend/app/registry.py: 2026-11-10T11:52:30
  backend/app/clients/model_server.py: 2026-11-10T11:52:30
  backend/app/routes/system.py: 2026-11-10T11:52:30
  backend/app/routes/chat.py: 2026-11-10T11:52:30
  frontend/Dockerfile: 2026-11-10T11:52:30
  frontend/Caddyfile: 2026-11-10T11:52:30
  deploy/docker-compose.prod.yml: 2026-11-10T11:52:30
  deploy/deploy.sh: 2026-11-10T11:52:30
  deploy/remote-deploy.sh: 2026-11-10T11:52:30
  deploy/.env.server.example: 2026-11-10T11:52:30
  deploy/README.md: 2026-11-10T11:52:30
  .github/workflows/ci.yml: 2026-11-10T11:52:30
  .github/workflows/deploy.yml: 2026-11-10T11:52:30
  .github/workflows/images.yml: 2026-11-10T11:52:30

## Spec (formal-spec; PRE / POST / INV / ERR / KILL when applicable)

PRE(dev):  repo root has `docker-compose.dev.yml`; `./backend/.env` optional (`required: false`).
PRE(colab): `pip install -r colab/requirements.txt` (+ `backend/requirements-ml.txt` for real models); env `MODEL_SERVER_TOKEN` recommended, `SERVER_USE_MOCKS=1` for stub run.
PRE(prod): GHCR images `sha-<7>` exist (workflow Images succeeded); `/opt/emotion-chatbot/.env` exists mode 600; network `javis-web` exists; DNS `emotion.hiennguyen.io.vn` → realestate-vm.
POST(colab): `GET /health` ⇒ `{"ok":true,"modules":["emotion","speech","llm"],"mocks":<bool>}`; stub module (`NotImplementedError`) ⇒ HTTP 501.
POST(dev):  UI `http://localhost:5173`, API `http://localhost:8000`; or single-container `http://localhost:8080`.
POST(prod): `https://emotion.hiennguyen.io.vn/api/health` ⇒ 200 within 12×5s retries.
INV1: backend routes mounted under `/api` prefix (`chat`, `system`, `feedback`) [backend/app/main.py:41-43].
INV2: `safety` and `music` modes ∈ {mock, local} only; `remote` rejected at startup [backend/app/config.py:91-96].
INV3: `MODEL_SERVER_URL` required when any module mode = remote [backend/app/config.py:97-101].
INV4: ML libs (`torch`,`transformers`,`librosa`) imported inside function bodies, never at module top [backend/requirements-ml.txt:2].
ERR: model-server stub not implemented ⇒ HTTP 501 [colab/server_app.py:69-71]; backend treats as error → fallback (emotion=Other, Gemini/soạn sẵn) [colab/README.md:93].
KILL: invalid `*_MODE` value stops app at `create_app()` [backend/app/config.py:75-78, backend/app/main.py:31-32].

## File map (scored + relationships)

### Scored files.

| rank | score | file | role | evidence (file:line) |
|------|-------|------|------|----------------------|
| 1 | 0.98 | colab/server_app.py | FastAPI model server: loads modules, defines /health /emotion /transcribe /prosody /generate, token gate | colab/server_app.py:85-117 |
| 2 | 0.95 | docker-compose.dev.yml | Dev compose: backend uvicorn reload :8000 + frontend node:22 Vite :5173 | docker-compose.dev.yml:6-51 |
| 3 | 0.93 | backend/.env.example | All env vars + defaults (MODEL_MODE, timeouts, MODEL_SERVER_*, GEMINI_*, CORS_ORIGINS) | backend/.env.example:4-62 |
| 4 | 0.92 | deploy/docker-compose.prod.yml | Prod compose: GHCR images, mem limits, javis-web caddy labels, emotion-data volume | deploy/docker-compose.prod.yml:6-32 |
| 5 | 0.92 | deploy/remote-deploy.sh | Server-side forced command: fetch compose per-commit, pull sha tag, up --wait, prune old images | deploy/remote-deploy.sh:52-82 |
| 6 | 0.90 | .github/workflows/images.yml | Build+push api (target base) & web images to GHCR with sha-/latest tags, GHA cache | .github/workflows/images.yml:44-72 |
| 7 | 0.90 | .github/workflows/deploy.yml | Triggered after Images; SSH `deploy <sha>` to server; health-check domain 12× | .github/workflows/deploy.yml:67-90 |
| 8 | 0.88 | .github/workflows/ci.yml | PR/push CI: backend (pip requirements-dev, ruff, pytest) + frontend (pnpm lint/test/build) | .github/workflows/ci.yml:16-55 |
| 9 | 0.88 | backend/app/clients/model_server.py | httpx async client: /emotion /transcribe /prosody /generate /health, schema validation, cached health | backend/app/clients/model_server.py:133-187 |
| 10 | 0.86 | backend/app/registry.py | Resolves module func by mode (mock/local/remote); remote → model_server client; safety/music not remote | backend/app/registry.py:52-68 |
| 11 | 0.85 | backend/app/main.py | FastAPI app: lifespan (validate_remote + model_server.startup/shutdown), routers under /api | backend/app/main.py:17-43 |
| 12 | 0.83 | backend/app/config.py | Settings(BaseSettings): all env fields + defaults + validate_remote + module_mode/module_timeout | backend/app/config.py:11-101 |
| 13 | 0.80 | backend/requirements.txt | Light runtime deps: fastapi, uvicorn[standard], pydantic, pydantic-settings, python-multipart, httpx | backend/requirements.txt:1-6 |
| 14 | 0.80 | backend/requirements-ml.txt | ML deps (lazy, local mode only): torch, transformers, librosa | backend/requirements-ml.txt:3-5 |
| 15 | 0.78 | backend/Dockerfile | base target (no torch) + ml target (torch CPU); ffmpeg; user app; HEALTHCHECK /api/health | backend/Dockerfile:4-45 |
| 16 | 0.75 | deploy/deploy.sh | Manual deploy: ssh realestate-vm → remote-deploy.sh under user deploy; curl /api/health 12× | deploy/deploy.sh:11-26 |
| 17 | 0.72 | frontend/Dockerfile | node:22 build (pnpm) → caddy:2-alpine serving /srv dist on :80 | frontend/Dockerfile:2-20 |
| 18 | 0.70 | frontend/Caddyfile | :80 serves static + reverse_proxy /api/* → BACKEND_UPSTREAM:8000 (6MB body, 90s read) | frontend/Caddyfile:6-26 |
| 19 | 0.70 | colab/requirements.txt | Colab server deps (same as backend minus httpx; ML via requirements-ml.txt) | colab/requirements.txt:2-5 |
| 20 | 0.65 | backend/app/routes/system.py | /api/health /api/meta /api/session/{id}; health reports model_server cached status | backend/app/routes/system.py:15-37 |
| 21 | 0.60 | backend/app/constants.py | LABELS(7), GOALS(4), MODULE_NAMES(5), MODES(3), AROUSAL_LEVELS(3) | backend/app/constants.py:3-11 |
| 22 | 0.55 | deploy/.env.server.example | Server .env template: MODEL_MODE=mock default, CORS to prod domain | deploy/.env.server.example:5-25 |
| 23 | 0.50 | deploy/README.md | Prod architecture + prerequisites + auto/manual deploy + rollback + ops runbook | deploy/README.md:1-105 |
| 24 | 0.45 | docker-compose.yml | Single-container local: backend + web(Caddy) :8080 with healthcheck | docker-compose.yml:5-32 |
| 25 | 0.40 | backend/requirements-dev.txt | Dev/test deps: -r requirements.txt + pytest, pytest-asyncio, ruff, imageio-ffmpeg, respx | backend/requirements-dev.txt:1-5 |
| 26 | 0.40 | colab/README.md | Colab runbook: HTTP contract table, dev mock run, Colab T4 cells, ngrok static domain, .env mapping | colab/README.md:1-95 |

### Relationships (formal-spec).

CONTRACTS:
  - F := scored_files.
  - rel: F × F × KIND → bool. KIND ∈ { imports, calls, inherits, configures, tests, references, defines, triggered_by, depends_on }.

EDGES:
  rel(colab/server_app.py, backend/modules/emotion.py, imports) ⇒ colab/server_app.py:26-28,50-52
  rel(colab/server_app.py, backend/mocks/emotion.py, imports) ⇒ colab/server_app.py:51-52
  rel(colab/server_app.py, backend/modules/speech.py, calls) ⇒ colab/server_app.py:99,103
  rel(colab/server_app.py, backend/modules/llm.py, calls) ⇒ colab/server_app.py:107-114
  rel(backend/app/main.py, backend/app/clients/model_server.py, calls) ⇒ backend/app/main.py:9,20,24
  rel(backend/app/main.py, backend/app/routes/chat.py, imports) ⇒ backend/app/main.py:12,41
  rel(backend/app/main.py, backend/app/routes/system.py, imports) ⇒ backend/app/main.py:12,42
  rel(backend/app/main.py, backend/app/routes/feedback.py, imports) ⇒ backend/app/main.py:12,43
  rel(backend/app/main.py, backend/app/config.py, calls) ⇒ backend/app/main.py:10,19,31-32
  rel(backend/app/registry.py, backend/app/clients/model_server.py, calls) ⇒ backend/app/registry.py:62-64
  rel(backend/app/registry.py, backend/app/config.py, depends_on) ⇒ backend/app/registry.py:9,49
  rel(backend/app/clients/model_server.py, colab/server_app.py, references) ⇒ backend/app/clients/model_server.py:135,151,156,175 (paths /emotion /transcribe /prosody /generate)
  rel(backend/app/config.py, backend/app/constants.py, imports) ⇒ backend/app/config.py:8
  rel(backend/app/routes/system.py, backend/app/registry.py, calls) ⇒ backend/app/routes/system.py:5,17,29
  rel(backend/app/routes/system.py, backend/app/clients/model_server.py, calls) ⇒ backend/app/routes/system.py:6,20
  rel(docker-compose.dev.yml, backend/Dockerfile, configures) ⇒ docker-compose.dev.yml:7-9 (target base)
  rel(docker-compose.dev.yml, backend/.env.example, configures) ⇒ docker-compose.dev.yml:20-26
  rel(deploy/docker-compose.prod.yml, .github/workflows/images.yml, depends_on) ⇒ deploy/docker-compose.prod.yml:7,16 (ghcr images built by images.yml)
  rel(.github/workflows/deploy.yml, .github/workflows/images.yml, triggered_by) ⇒ .github/workflows/deploy.yml:6-9
  rel(.github/workflows/deploy.yml, deploy/remote-deploy.sh, calls) ⇒ .github/workflows/deploy.yml:77
  rel(deploy/deploy.sh, deploy/remote-deploy.sh, calls) ⇒ deploy/deploy.sh:15
  rel(deploy/remote-deploy.sh, deploy/docker-compose.prod.yml, references) ⇒ deploy/remote-deploy.sh:16,60,67-68
  rel(backend/Dockerfile, backend/requirements.txt, references) ⇒ backend/Dockerfile:17-18
  rel(backend/Dockerfile, backend/requirements-ml.txt, references) ⇒ backend/Dockerfile:43-44
  rel(frontend/Dockerfile, frontend/Caddyfile, references) ⇒ frontend/Dockerfile:17
  rel(colab/README.md, colab/server_app.py, references) ⇒ colab/README.md:3,24
  rel(.github/workflows/ci.yml, backend/requirements-dev.txt, references) ⇒ .github/workflows/ci.yml:31
  rel(backend/app/clients/model_server.py, backend/app/constants.py, imports) ⇒ backend/app/clients/model_server.py:17

### Topology.

  - entry_point := colab/server_app.py:120 (`app = create_app()`) for Colab path; backend/app/main.py:50 (`app = create_app()`) for backend path.
  - critical_path := docker-compose.dev.yml → backend/Dockerfile(target base) → backend/app/main.py → backend/app/registry.py → backend/app/clients/model_server.py → colab/server_app.py → backend/modules/*.py (or backend/mocks/*.py).
  - leaf_files := { backend/modules/emotion.py, backend/modules/speech.py, backend/modules/llm.py, backend/mocks/emotion.py, backend/mocks/speech.py, backend/mocks/llm.py, backend/app/constants.py, frontend/Caddyfile, backend/requirements.txt, backend/requirements-ml.txt, colab/requirements.txt, deploy/.env.server.example, backend/.env.example }.

## Behavior (input → process → output, 运行时视图)

- input: HTTP requests hit either Colab model server (`POST /emotion` JSON `{text}`, `POST /transcribe|/prosody` multipart `file` WAV 16kHz mono, `POST /generate` JSON `{text,emotion,arousal,history,goal}`) [colab/server_app.py:34-43,93-115] or backend (`/api/chat`, `/api/health`, `/api/meta`, `/api/session/{id}`, `/api/feedback/*`) [backend/app/main.py:41-43]. Backend reads env via `Settings(BaseSettings)` from `.env` [backend/app/config.py:11-14].
- process: (1) backend `create_app()` runs `validate_remote()` → fails fast on bad mode/missing URL [backend/app/main.py:31-32, backend/app/config.py:89-101]; (2) lifespan starts shared `httpx.AsyncClient` for model server [backend/app/main.py:18-24, backend/app/clients/model_server.py:77-81]; (3) `registry.get(name,func)` resolves impl by mode: remote → `model_server.*` client, mock → `mocks.*`, local → `modules.*` [backend/app/registry.py:52-68]; (4) Colab `create_app()` dynamically imports `backend/{modules,mocks}.{emotion,speech,llm}` via `importlib` [colab/server_app.py:50-52]; (5) sync module fns run in threadpool; `NotImplementedError` → HTTP 501 [colab/server_app.py:65-71]; (6) `/api/health` reports `model_server` cached status (10s TTL) when any module remote [backend/app/routes/system.py:15-20, backend/app/clients/model_server.py:190-198]; (7) prod deploy: `images.yml` builds GHCR images → `deploy.yml` SSH `deploy <sha>` → `remote-deploy.sh` fetches per-commit compose, `pull`, `up -d --wait`, prunes old tags [deploy/remote-deploy.sh:52-82].
- output: Colab `/emotion` ⇒ `{label,probs}` (7 LABELS); `/transcribe` ⇒ `{text}`; `/prosody` ⇒ `{arousal,pitch_mean?,energy_rms?,speech_rate?}`; `/generate` ⇒ `{reply}`; `/health` ⇒ `{ok:true,modules,mocks}` [colab/server_app.py:89-115, colab/README.md:7-13, backend/app/clients/model_server.py:34-65]. Backend `/api/health` ⇒ `HealthResponse{ok,model_server}` [backend/app/routes/system.py:15-20].
- side_effects: backend writes `data/runtime/feedback.jsonl` (FEEDBACK_PATH) [backend/.env.example:31]; prod mounts `emotion-data` volume → `/app/data/runtime` [deploy/docker-compose.prod.yml:11-12]; Colab opens ngrok tunnel (external network egress) [colab/README.md:72-77]; `remote-deploy.sh` runs `docker rmi` on old project images [deploy/remote-deploy.sh:77-80]; CI runs `pytest` (no filesystem writes beyond CI runner).

## Findings (cite file:line)

### (1) Colab model server startup, model classes, endpoints, contracts

- Startup: `uvicorn server_app:app --host 0.0.0.0 --port 8001` run from `colab/` dir [colab/server_app.py:7, colab/README.md:24,67-69]. `app = create_app()` at module import [colab/server_app.py:120].
- Model classes loaded: NO model classes live in `server_app.py` itself — it is a thin "khung" (frame) [colab/server_app.py:1-5]. It dynamically imports `backend/modules/{emotion,speech,llm}` (real ML) or `backend/mocks/{emotion,speech,llm}` (stubs) via `importlib.import_module` based on `SERVER_USE_MOCKS` env [colab/server_app.py:46-52]. `SERVED_MODULES = ("emotion", "speech", "llm")` [colab/server_app.py:30]. Safety and music are NOT served here [colab/README.md:17].
- Endpoints exposed (5 total):
  - `GET /health` → `{"ok":True,"modules":[...],"mocks":<bool>}`, no token required [colab/server_app.py:89-91, colab/README.md:13].
  - `POST /emotion` — in: JSON `EmotionIn{text:str}`; out: result of `predict_emotion(text)` = `{label,probs}` [colab/server_app.py:93-95, colab/README.md:9].
  - `POST /transcribe` — in: multipart `file` (WAV 16kHz mono); out: `{"text": <str>}` [colab/server_app.py:97-99, colab/README.md:10].
  - `POST /prosody` — in: multipart `file`; out: `extract_prosody` result `{arousal,pitch_mean?,energy_rms?,speech_rate?}` [colab/server_app.py:101-103, colab/README.md:11, backend/app/clients/model_server.py:57-62].
  - `POST /generate` — in: JSON `GenerateIn{text,emotion,arousal?,history[],goal?}`; out: `{"reply": <str>}` [colab/server_app.py:105-115, colab/README.md:12].
- Auth contract: all routes except `/health` gated by `Depends(require_token)`; if `MODEL_SERVER_TOKEN` env set, header `X-Model-Server-Token` must match (constant-time compare) else HTTP 401 [colab/server_app.py:55-62,93,97,101,105]. If unset, no auth [colab/server_app.py:59-60].
- Error contract: module stub raising `NotImplementedError` → HTTP 501 "Module chưa được cài đặt" [colab/server_app.py:65-71]. Upload handling: writes UploadFile to tempdir `audio.wav`, runs fn in threadpool, cleans tempdir [colab/server_app.py:74-82].
- Pydantic request models: `EmotionIn{text:str}` [colab/server_app.py:34-35]; `GenerateIn{text:str,emotion:dict,arousal:str|None,history:list[dict],goal:str|None}` [colab/server_app.py:38-43].
- Real-model stubs (raise NotImplementedError, assigned to team members): `predict_emotion` (CafeBERT, 7 labels) [backend/modules/emotion.py:10-18]; `transcribe` (PhoWhisper) [backend/modules/speech.py:7-13]; `extract_prosody` (librosa) [backend/modules/speech.py:16-22]; `generate_reply` (Qwen3/Gemini) [backend/modules/llm.py:7-24].

### (2) Docker-compose dev: backend+frontend locally, required env vars, config defaults

- Run: `docker compose -f docker-compose.dev.yml up --build` [docker-compose.dev.yml:1]. Name `emotion-chatbot-dev` [docker-compose.dev.yml:3].
- Backend service: builds `./backend` target `base` [docker-compose.dev.yml:7-9]; command `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload` [docker-compose.dev.yml:10-19]; `env_file: ./backend/.env` (required: false) [docker-compose.dev.yml:20-22]; extra env `WATCHFILES_FORCE_POLLING=true` (Windows bind-mount polling), `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` [docker-compose.dev.yml:23-26]; bind mount `./backend:/app` [docker-compose.dev.yml:27-28]; port `8000:8000` [docker-compose.dev.yml:29-30].
- Frontend service: `node:22-alpine` image; `corepack prepare pnpm@11.17.0` then `pnpm install --frozen-lockfile && pnpm dev --host` [docker-compose.dev.yml:34-39]; env `CHOKIDAR_USEPOLLING=true`, `VITE_API_PROXY=http://backend:8000` [docker-compose.dev.yml:40-42]; volumes `./frontend:/app` + named `frontend-node-modules:/app/node_modules` [docker-compose.dev.yml:43-46]; port `5173:5173`; `depends_on: backend` [docker-compose.dev.yml:47-50].
- Single-container local alternative: `docker compose up --build` → `http://localhost:8080` [docker-compose.yml:1,27-28]. Builds backend (target base) + web (frontend Dockerfile, Caddy on :80) [docker-compose.yml:5-32]. Backend healthcheck hits `/api/health` [docker-compose.yml:14-18].
- Required env vars (from `backend/.env.example`): `MODEL_MODE` default `mock` [backend/.env.example:4]; per-module overrides `EMOTION_MODE/SPEECH_MODE/SAFETY_MODE/LLM_MODE/MUSIC_MODE` (blank ⇒ use MODEL_MODE) [backend/.env.example:8-12]; `MODEL_SERVER_URL` + `MODEL_SERVER_TOKEN` required when emotion/speech/llm remote [backend/.env.example:14-18]; remote timeouts `REMOTE_TIMEOUT_{EMOTION=10,TRANSCRIBE=20,PROSODY=10,GENERATE=30}` [backend/.env.example:21-24]; `GEMINI_API_KEY` (blank=skip) + `GEMINI_MODEL=gemini-3.6-flash` [backend/.env.example:27-28]; `FEEDBACK_PATH=data/runtime/feedback.jsonl`, `ADMIN_TOKEN` (blank=disable export) [backend/.env.example:31-32]; `SONGS_CSV=data/songs.csv` [backend/.env.example:35]; audio limits `MAX_AUDIO_SECONDS=30`, `MAX_AUDIO_MB=5` [backend/.env.example:38-39]; `FFMPEG_BINARY=ffmpeg` [backend/.env.example:42]; `HISTORY_TURNS=6` [backend/.env.example:45]; `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` [backend/.env.example:48]; module timeouts `SAFETY_TIMEOUT=5,EMOTION_TIMEOUT=10,LLM_TIMEOUT=30,MUSIC_TIMEOUT=5,SPEECH_TIMEOUT=20,PROSODY_TIMEOUT=10` [backend/.env.example:51-56]; `SAFETY_HOTLINE_TEXT` [backend/.env.example:59]; `MOCK_LATENCY_MS=0` [backend/.env.example:62].
- Config defaults mirror in code: `Settings` class [backend/app/config.py:16-53]; `MODEL_MODE="mock"` default; `MODES=["mock","local","remote"]` [backend/app/constants.py:9]; `LABELS` 7 emotions [backend/app/constants.py:3]; `MODULE_NAMES=["emotion","speech","safety","llm","music"]` [backend/app/constants.py:7].
- Mode validation: invalid `*_MODE` raises ValueError at `create_app()` [backend/app/config.py:75-78, backend/app/main.py:31-32]; `safety`/`music` cannot be remote [backend/app/config.py:91-96]; remote requires non-empty `MODEL_SERVER_URL` [backend/app/config.py:97-101].

### (3) deploy/*.sh + compose.prod.yml

- `deploy/docker-compose.prod.yml`: name `emotion-chatbot` [deploy/docker-compose.prod.yml:3]; backend image `ghcr.io/nguyentathien/emotion-chatbot-api:${TAG:-latest}`, `restart: unless-stopped`, `mem_limit: 512m`, `env_file: .env`, volume `emotion-data:/app/data/runtime`, network `internal` [deploy/docker-compose.prod.yml:6-13]; web image `...-web:${TAG:-latest}`, `mem_limit: 128m`, `depends_on: backend (service_healthy)`, networks `internal` + external `javis-web`, Caddy labels `caddy=emotion.hiennguyen.io.vn` + `caddy.reverse_proxy={{upstreams 80}}` [deploy/docker-compose.prod.yml:15-25]. Run: `TAG=sha-xxxxxxx docker compose -f docker-compose.prod.yml up -d` from `/opt/emotion-chatbot` [deploy/docker-compose.prod.yml:2].
- `deploy/deploy.sh`: manual deploy from dev machine; `git fetch origin main`, resolve SHA (arg or origin/main) [deploy/deploy.sh:11-12]; `ssh realestate-vm` runs `runuser -u deploy -- env SSH_ORIGINAL_COMMAND='deploy <SHA>' /opt/emotion-chatbot/remote-deploy.sh` [deploy/deploy.sh:15]; then curl `https://emotion.hiennguyen.io.vn/api/health` up to 12×5s [deploy/deploy.sh:17-26]. Defaults `DEPLOY_HOST=realestate-vm`, `DEPLOY_DOMAIN=emotion.hiennguyen.io.vn` [deploy/deploy.sh:8-9].
- `deploy/remote-deploy.sh`: runs ON server as SSH forced command (`restrict,command=...`) [deploy/README.md:48]; accepts `deploy <40-hex-sha>` or `status` [deploy/remote-deploy.sh:25-40]; validates SHA `^[0-9a-f]{40}$` [deploy/remote-deploy.sh:42-45]; requires `/opt/emotion-chatbot/.env` [deploy/remote-deploy.sh:47-50]; sets `TAG=sha-<7>` [deploy/remote-deploy.sh:52-54]; fetches `docker-compose.prod.yml` for that exact commit from `raw.githubusercontent.com` [deploy/remote-deploy.sh:56-63]; `docker compose pull` + `up -d --remove-orphans --wait --wait-timeout 180` [deploy/remote-deploy.sh:67-68]; saves `.tag`/`.tag-truoc` for rollback [deploy/remote-deploy.sh:71-74]; prunes old project images keeping current + previous [deploy/remote-deploy.sh:77-80].
- `deploy/.env.server.example`: server .env template; `MODEL_MODE=mock` default; remote mode instructions; `GEMINI_API_KEY/MODEL`; `ADMIN_TOKEN`; `SAFETY_HOTLINE_TEXT`; `CORS_ORIGINS=https://emotion.hiennguyen.io.vn` [deploy/.env.server.example:5-25]. Created manually on server, never copied from dev [deploy/.env.server.example:1-2, deploy/README.md:32].
- Architecture: Internet:443 → `javis-proxy` (caddy-docker-proxy, network `javis-web`) → `web` (Caddy static + proxy /api/*) → `backend` (FastAPI :8000, no published port); only `web` joins `javis-web`, backend stays internal [deploy/README.md:7-18].

### (4) GitHub workflows

- `ci.yml` (name CI): triggers on `pull_request` + `push` to `main` [.github/workflows/ci.yml:3-6]; concurrency cancels in-progress [.github/workflows/ci.yml:11-13]. Two jobs:
  - `backend` (working-dir `backend`): checkout, setup-python 3.11 (pip cache keyed on `requirements*.txt`), `apt-get install ffmpeg`, `pip install -r requirements-dev.txt`, `ruff check .`, `pytest` [.github/workflows/ci.yml:16-35].
  - `frontend` (working-dir `frontend`): checkout, pnpm 11.17.0, node 22 (pnpm cache), `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm test`, `pnpm build` [.github/workflows/ci.yml:37-55].
- `images.yml` (name Images): triggers on `push` to `main` + `workflow_dispatch` [.github/workflows/images.yml:3-7]; permissions `packages: write` [.github/workflows/images.yml:8-10]. Single job `build-push`: buildx, login to `ghcr.io` with `GITHUB_TOKEN`; API image `ghcr.io/nguyentathien/emotion-chatbot-api` built from `backend` context **target `base`** with tags `sha-<short>` + `latest`, GHA cache scope `api` [.github/workflows/images.yml:35-53]; web image `...-web` from `frontend` context, tags `sha-<short>` + `latest`, GHA cache scope `web` [.github/workflows/images.yml:55-72].
- `deploy.yml` (name Deploy): triggers `workflow_run` on Images `completed` (branch main) + `workflow_dispatch` with `sha` input [.github/workflows/deploy.yml:5-15]; concurrency `deploy-production` no cancel [.github/workflows/deploy.yml:20-22]; runs only if Images succeeded on push event, or manual dispatch [.github/workflows/deploy.yml:29-31]; environment `production` (url `https://emotion.hiennguyen.io.vn`), timeout 15m [.github/workflows/deploy.yml:33-36]. Steps: choose SHA (workflow_run.head_sha / input / dispatch sha), validate 40-hex [.github/workflows/deploy.yml:38-55]; configure SSH from secrets `DEPLOY_SSH_KEY/DEPLOY_KNOWN_HOSTS` [.github/workflows/deploy.yml:57-65]; `ssh ... "deploy $SHA"` to server [.github/workflows/deploy.yml:67-77]; health-check `$APP_URL/api/health` 12×5s [.github/workflows/deploy.yml:79-90]; always rm deploy key [.github/workflows/deploy.yml:92-93]. Rollback = manual run with old 40-hex SHA [.github/workflows/deploy.yml:3-4, deploy/README.md:73-75].

### (5) requirements.txt vs requirements-ml.txt (and dev/colab)

- `backend/requirements.txt` (6 pkgs, light runtime, installed in `base` Docker target): `fastapi>=0.115`, `uvicorn[standard]>=0.30`, `pydantic>=2.7`, `pydantic-settings>=2.3`, `python-multipart>=0.0.9`, `httpx>=0.27` [backend/requirements.txt:1-6]. httpx is the remote-mode client transport [backend/app/clients/model_server.py:13].
- `backend/requirements-ml.txt` (3 pkgs, `local` mode only, NOT installed in base/prod image): `torch`, `transformers`, `librosa` [backend/requirements-ml.txt:3-5]. Rule: these MUST be imported inside function bodies, never at module top (keeps `base` importable without torch) [backend/requirements-ml.txt:2]. Installed in `ml` Docker target via `--extra-index-url https://download.pytorch.org/whl/cpu` [backend/Dockerfile:40-44]. On Colab, installed alongside `colab/requirements.txt` [colab/README.md:45].
- `backend/requirements-dev.txt`: `-r requirements.txt` + `pytest>=8`, `pytest-asyncio>=0.23`, `ruff>=0.5`, `imageio-ffmpeg>=0.5`, `respx>=0.21` [backend/requirements-dev.txt:1-5]. Used by CI [ci.yml:31].
- `colab/requirements.txt`: same as backend runtime minus httpx (server doesn't call itself) — `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `python-multipart` [colab/requirements.txt:2-5]; ML deps added separately via `requirements-ml.txt` [colab/requirements.txt:1].

## Next reads (若 scope 对消费者不足)

- About `/api/chat` full request/response schema (ChatRequest/ChatResponse fields) → backend/app/schemas.py + backend/app/routes/chat.py:23-24.
- About pipeline orchestration (emotion→safety→llm→music ordering, arousal wiring) → backend/app/pipeline.py:1-57.
- About module ML internals (CafeBERT/PhoWhisper/Qwen3 loading, fp16, lazy import pattern) → backend/modules/emotion.py:10-18, backend/modules/speech.py:7-22, backend/modules/llm.py:7-24, colab/README.md:57-60.
- About Gemini fallback flow → backend/app/gemini.py + backend/app/fallbacks.py:56-57.
- About feedback CSV export route contract → backend/app/routes/feedback.py.
- About session store (in-memory, MAX_SESSIONS) → backend/app/session.py + backend/app/constants.py:13-15.
- About ngrok static-domain setup + Colab notebook cells → colab/README.md:36-81.
- About frontend API client (endpoints, audio upload) → frontend/src/lib/api.ts + frontend/src/lib/api-audio.test.ts.

## Gherkin scenarios (≥ 1 when applicable)

```gherkin
Feature: Runbook — Colab model server endpoints
  Scenario: /health returns module list without token
    Given colab/server_app.py running with SERVER_USE_MOCKS=1 and MODEL_SERVER_TOKEN set
    When a client sends GET /health
    Then response is {"ok": true, "modules": ["emotion","speech","llm"], "mocks": true}
    And no X-Model-Server-Token header was required
    # colab/server_app.py:89-91

  Scenario: stub module returns HTTP 501
    Given a real module function raises NotImplementedError
    When a client sends POST /emotion with {"text": "hello"}
    Then response status is 501 with detail "Module chưa được cài đặt."
    # colab/server_app.py:65-71

  Scenario: token-gated route rejects missing token
    Given MODEL_SERVER_TOKEN=secret is set on the server
    When a client sends POST /emotion without X-Model-Server-Token header
    Then response status is 401
    # colab/server_app.py:55-62, 93

Feature: Runbook — dev compose boots backend + frontend
  Scenario: docker compose dev up
    Given docker-compose.dev.yml and optional ./backend/.env
    When running `docker compose -f docker-compose.dev.yml up --build`
    Then backend is reachable at http://localhost:8000 with --reload
    And frontend Vite dev server is reachable at http://localhost:5173
    And frontend proxies API calls to http://backend:8000
    # docker-compose.dev.yml:10-50

Feature: Runbook — prod deploy chain
  Scenario: push to main auto-deploys
    Given a push to main and workflow Images completes successfully
    When workflow Deploy triggers (workflow_run completed success on push)
    Then it SSHs to realestate-vm running `deploy <40-hex-sha>`
    And remote-deploy.sh fetches docker-compose.prod.yml for that commit
    And pulls ghcr images tagged sha-<7> and runs `up -d --wait`
    And https://emotion.hiennguyen.io.vn/api/health returns 200 within 12×5s
    # .github/workflows/deploy.yml:29-90, deploy/remote-deploy.sh:52-82

  Scenario: rollback to prior commit
    Given a previous commit SHA (40 hex) with an existing GHCR image
    When manually running workflow Deploy with inputs.sha = <old SHA>
    Then remote-deploy.sh deploys sha-<old7> tag
    # .github/workflows/deploy.yml:10-15, deploy/README.md:73-75

Feature: Runbook — requirements split keeps base image light
  Scenario: base image runs mock/remote without torch
    Given backend/Dockerfile target base installs only requirements.txt
    Then the image has fastapi, uvicorn, pydantic, httpx but NOT torch/transformers/librosa
    And mock and remote modes work because ML libs are imported lazily inside function bodies
    # backend/Dockerfile:17-18,40-44, backend/requirements-ml.txt:2
```
