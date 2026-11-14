# ANSWER

## TL;DR (≤ 5 行, AI 5 秒可读)

- answer: `src/lib/api.ts` implements the API client (sendChat → POST /api/chat multipart FormData; getMeta → GET /api/meta; getHealth → GET /api/health). Data flow: ChatView calls useSession() → sessionId → useChat(sessionId, goal) → sendChat/sendVoice via chatReducer. Voice path: useVoiceRecording = useRecorder (MediaRecorder blob) + useSpeechFallback (Web Speech vi-VN transcript hint); playback is local `<audio>` replay only — no TTS. App.tsx wraps ChatView in ThemeProvider → TooltipProvider → Toaster.
- scope_in: [API client (api.ts) request/response for /api/chat, /api/meta, /api/health; useChat ← useSession ← ChatView data flow; voice recording + upload + playback path; components/chat, components/music, components/emotion render structure; App.tsx top-level layout and providers].
- scope_out: [Backend implementation of /api/chat handler; useTypewriter animation internals; theme-provider.tsx theme switching mechanism; storage.ts localStorage key scheme; AppSidebar conversation history rendering detail; EmptyState suggested prompts; SafetyAlert/StatusBadge internal rendering; lib/emotion-meta.ts emotion label/icon mapping; lib/goals.ts goal definitions; lib/youtube.ts URL parsing].
- stale_check: git_head=ceb62f9; 用 `git diff HEAD -- src/lib/api.ts src/hooks/useChat.ts src/components/chat/ChatView.tsx` 验证。

## Frontmatter
created: 2026-11-10T11:55:22Z
question: Map the frontend: API client for /api/chat, /api/meta, /api/health; data flow useChat ← useSession ← components/chat; voice path; component structure; App.tsx layout.
posterior_final: 0.95
rg_calls_used: 3
engine: opencode
git_head: ceb62f9
git_branch: main
files_verified_mtime:
  src/lib/api.ts: 2026-11-10T11:52:30
  src/hooks/useChat.ts: 2026-11-10T11:52:30
  src/hooks/useSession.ts: 2026-11-10T11:52:30
  src/hooks/useRecorder.ts: 2026-11-10T11:52:30
  src/hooks/useVoiceRecording.ts: 2026-11-10T11:52:30
  src/hooks/useSpeechFallback.ts: 2026-11-10T11:52:30
  src/hooks/useMeta.ts: 2026-11-10T11:52:30
  src/hooks/chat-state.ts: 2026-11-10T11:52:30
  src/lib/api-types.gen.ts: 2026-11-10T11:52:30
  src/components/chat/ChatView.tsx: 2026-11-10T11:52:30
  src/components/chat/PromptBar.tsx: 2026-11-10T11:52:30
  src/components/chat/BotMessage.tsx: 2026-11-10T11:52:30
  src/components/chat/UserMessage.tsx: 2026-11-10T11:52:30
  src/components/chat/MessageList.tsx: 2026-11-10T11:52:30
  src/components/chat/VoiceBubble.tsx: 2026-11-10T11:52:30
  src/components/chat/RecordingBar.tsx: 2026-11-10T11:52:30
  src/components/chat/RecordButton.tsx: 2026-11-10T11:52:30
  src/components/chat/ChatHeader.tsx: 2026-11-10T11:52:30
  src/components/emotion/EmotionChip.tsx: 2026-11-10T11:52:30
  src/components/emotion/EmotionDetail.tsx: 2026-11-10T11:52:30
  src/components/music/SongList.tsx: 2026-11-10T11:52:30
  src/components/music/SongCard.tsx: 2026-11-10T11:52:30
  src/components/music/SongPlayerDialog.tsx: 2026-11-10T11:52:30
  src/App.tsx: 2026-11-10T11:52:30
  src/main.tsx: 2026-11-10T11:52:30
  package.json: 2026-11-10T11:52:30

## Spec (formal-spec; PRE / POST / INV / ERR / KILL when applicable)

PRE: repo /Users/quiniu/fsb/NLP/final_project/emotion-chatbot; frontend is Vite+TS+React 19, shadcn/ui, Tailwind v4, pnpm.
INV1: ∀ API call originates from src/lib/api.ts; no inline fetch elsewhere except api.ts.
INV2: useChat is the sole mutation entrypoint for chat state; chatReducer is the sole state transition function.
INV3: Voice recording uses MediaRecorder (useRecorder) for audio blob + Web Speech API (useSpeechFallback) for transcript hint; these run in parallel.
INV4: No TTS / SpeechSynthesis in frontend (verified: rg "SpeechSynthesis" → 0 hits).
INV5: Types are auto-generated from backend openapi.json via `openapi-typescript` (package.json:12).
ERR: HTTP non-ok → `toApiError()` parses JSON `{detail: string | [{msg}]}` → throws `ApiError{status, detail}` (api.ts:25-36,14-23).
KILL: findings not grounded in located file → dropped.

## File map (scored + relationships)

### Scored files.

| rank | score | file | role | evidence (file:line) |
|------|-------|------|------|----------------------|
| 1 | 0.98 | src/lib/api.ts | API client: sendChat (POST /api/chat multipart), getMeta (GET /api/meta), getHealth (GET /api/health), getSession, sendFeedback; ApiError class | api.ts:60-82, api.ts:105-109, api.ts:14-23 |
| 2 | 0.97 | src/hooks/useChat.ts | Chat orchestrator hook: useReducer(chatReducer), send/sendVoice/retry/rate, session hydration via getSession | useChat.ts:41-226, useChat.ts:93-124, useChat.ts:130-181 |
| 3 | 0.95 | src/components/chat/ChatView.tsx | Top-level chat component: calls useSession+useChat+useMeta, renders SidebarProvider+AppSidebar+ChatHeader+MessageList/EmptyState+PromptBar, aurora mood background | ChatView.tsx:40-165 |
| 4 | 0.93 | src/hooks/chat-state.ts | Chat state: ChatMessage types, chatReducer (send/resolve/rate/fail/retry/switch/hydrate), toStored, turnsToMessages, audioUrlsOf | chat-state.ts:83-174, chat-state.ts:204-232 |
| 5 | 0.92 | src/hooks/useVoiceRecording.ts | Composes useRecorder + useSpeechFallback into unified voice recording API; exposes start/send/cancel, liveText | useVoiceRecording.ts:11-68 |
| 6 | 0.90 | src/hooks/useRecorder.ts | MediaRecorder wrapper: getUserMedia, MIME selection, 30s max, 250ms timeslice, blob output, error classification | useRecorder.ts:118-272, useRecorder.ts:7-11 |
| 7 | 0.88 | src/hooks/useSpeechFallback.ts | Web Speech API (vi-VN) parallel transcription; provides transcriptHint; all errors swallowed (no-op fallback) | useSpeechFallback.ts:54-134, useSpeechFallback.ts:92 |
| 8 | 0.87 | src/hooks/useSession.ts | Session management: loadOrCreate from localStorage, conversation list (max 50), switch/new/delete | useSession.ts:59-135 |
| 9 | 0.85 | src/hooks/useMeta.ts | Fetches /api/meta on mount + polls /api/health every 30s (visibility-aware); returns meta/failed/modelServer | useMeta.ts:13-56 |
| 10 | 0.85 | src/lib/api-types.gen.ts | Auto-generated OpenAPI types: ChatResponse, Emotion, Song, Meta, MetaResponse, HealthResponse, SessionResponse, SessionTurn | api-types.gen.ts:127-273 |
| 11 | 0.82 | src/components/chat/PromptBar.tsx | Input bar: GoalPicker + RecordButton + Textarea + Send; instantiates useVoiceRecording; RecordingBar when active; IME-safe Enter handling | PromptBar.tsx:37-139, PromptBar.tsx:60 |
| 12 | 0.80 | src/components/chat/BotMessage.tsx | Renders bot reply: Bubble with typewriter effect, SafetyAlert if safety, SongList, FeedbackButtons | BotMessage.tsx:16-43 |
| 13 | 0.78 | src/components/chat/UserMessage.tsx | Renders user message: Bubble, VoiceBubble for voice kind, EmotionChip+ArousalChip when sent+emotion, retry button on error | UserMessage.tsx:15-82 |
| 14 | 0.75 | src/components/chat/MessageList.tsx | Scrollable message list: MessageScroller, maps ChatMessage → UserMessage/BotMessage, TypingIndicator when pending | MessageList.tsx:23-67 |
| 15 | 0.72 | src/components/chat/VoiceBubble.tsx | Voice playback: Play/Pause local `<audio>` from object URL, transcript text, pending state | VoiceBubble.tsx:16-88 |
| 16 | 0.70 | src/components/chat/ChatHeader.tsx | Header: bot avatar+connection status, title, StatusBadge, ThemeToggle, new conversation button | ChatHeader.tsx:29-93 |
| 17 | 0.65 | src/components/emotion/EmotionChip.tsx | Popover badge: emotion label + %, opens EmotionDetail; also exports ArousalChip | EmotionChip.tsx:21-45, EmotionChip.tsx:47-57 |
| 18 | 0.63 | src/components/emotion/EmotionDetail.tsx | Popover content: sorted Progress bars for all emotion probabilities + disclaimer | EmotionDetail.tsx:6-45 |
| 19 | 0.62 | src/components/music/SongList.tsx | Responsive song grid: horizontal snap on mobile, CSS grid on desktop; renders SongCards + SongPlayerDialog | SongList.tsx:6-29 |
| 20 | 0.60 | src/components/music/SongCard.tsx | Song card: 16:9 YouTube thumbnail, title/artist/reason, play→dialog or external link | SongCard.tsx:25-113 |
| 21 | 0.58 | src/components/music/SongPlayerDialog.tsx | YouTube iframe embed dialog: prev/next navigation, strip thumbnail playlist, keyboard arrows | SongPlayerDialog.tsx:52-213 |
| 22 | 0.55 | src/components/chat/RecordingBar.tsx | Recording UI: timer (formatClock), live transcript preview, cancel/send buttons | RecordingBar.tsx:16-75 |
| 23 | 0.50 | src/components/chat/RecordButton.tsx | Mic button: aria-label, disabled/busy states | RecordButton.tsx:11-25 |
| 24 | 0.45 | src/App.tsx | Root component: ThemeProvider > TooltipProvider > ChatView + Toaster | App.tsx:6-15 |
| 25 | 0.40 | src/main.tsx | Entry point: createRoot → StrictMode → App | main.tsx:7-11 |

### Relationships (formal-spec).

CONTRACTS:
  - F := scored_files.
  - rel: F × F × KIND → bool. KIND ∈ { imports, calls, inherits, configures, tests, references, defines, triggered_by, depends_on }.

EDGES:
  rel(main.tsx, App.tsx, imports) ⇒ main.tsx:5
  rel(App.tsx, ChatView.tsx, imports) ⇒ App.tsx:1
  rel(App.tsx, theme-provider.tsx, imports) ⇒ App.tsx:2
  rel(ChatView.tsx, useSession.ts, calls) ⇒ ChatView.tsx:5, ChatView.tsx:41-48
  rel(ChatView.tsx, useChat.ts, calls) ⇒ ChatView.tsx:3, ChatView.tsx:50-59
  rel(ChatView.tsx, useMeta.ts, calls) ⇒ ChatView.tsx:4, ChatView.tsx:60
  rel(useChat.ts, api.ts, calls) ⇒ useChat.ts:2, useChat.ts:98, useChat.ts:60, useChat.ts:203
  rel(useChat.ts, chat-state.ts, imports) ⇒ useChat.ts:7-14
  rel(useChat.ts, useRecorder.ts, imports) ⇒ useChat.ts:5
  rel(useChat.ts, useVoiceRecording.ts, imports) ⇒ useChat.ts:6
  rel(useMeta.ts, api.ts, calls) ⇒ useMeta.ts:2-7, useMeta.ts:22, useMeta.ts:38
  rel(api.ts, api-types.gen.ts, imports) ⇒ api.ts:1
  rel(useVoiceRecording.ts, useRecorder.ts, calls) ⇒ useVoiceRecording.ts:2, useVoiceRecording.ts:22
  rel(useVoiceRecording.ts, useSpeechFallback.ts, calls) ⇒ useVoiceRecording.ts:3, useVoiceRecording.ts:15
  rel(PromptBar.tsx, useVoiceRecording.ts, calls) ⇒ PromptBar.tsx:13-16, PromptBar.tsx:60
  rel(PromptBar.tsx, RecordButton.tsx, imports) ⇒ PromptBar.tsx:19
  rel(PromptBar.tsx, RecordingBar.tsx, imports) ⇒ PromptBar.tsx:20
  rel(MessageList.tsx, BotMessage.tsx, imports) ⇒ MessageList.tsx:12
  rel(MessageList.tsx, UserMessage.tsx, imports) ⇒ MessageList.tsx:14
  rel(BotMessage.tsx, SongList.tsx, imports) ⇒ BotMessage.tsx:3
  rel(BotMessage.tsx, useTypewriter.ts, calls) ⇒ BotMessage.tsx:6, BotMessage.tsx:17
  rel(UserMessage.tsx, EmotionChip.tsx, imports) ⇒ UserMessage.tsx:6
  rel(UserMessage.tsx, VoiceBubble.tsx, imports) ⇒ UserMessage.tsx:8
  rel(EmotionChip.tsx, EmotionDetail.tsx, imports) ⇒ EmotionChip.tsx:12
  rel(SongList.tsx, SongCard.tsx, imports) ⇒ SongList.tsx:3
  rel(SongList.tsx, SongPlayerDialog.tsx, imports) ⇒ SongList.tsx:4
  rel(SongCard.tsx, youtube.ts, calls) ⇒ SongCard.tsx:5
  rel(SongPlayerDialog.tsx, youtube.ts, calls) ⇒ SongPlayerDialog.tsx:13
  rel(RecordingBar.tsx, useRecorder.ts, references) ⇒ RecordingBar.tsx:3
  rel(VoiceBubble.tsx, useRecorder.ts, references) ⇒ VoiceBubble.tsx:4
  rel(ChatView.tsx, ChatHeader.tsx, imports) ⇒ ChatView.tsx:12
  rel(ChatView.tsx, AppSidebar.tsx, imports) ⇒ ChatView.tsx:11
  rel(ChatView.tsx, MessageList.tsx, imports) ⇒ ChatView.tsx:14
  rel(ChatView.tsx, PromptBar.tsx, imports) ⇒ ChatView.tsx:15
  rel(ChatView.tsx, emotion-meta.ts, calls) ⇒ ChatView.tsx:9, ChatView.tsx:117

### Topology.

  - entry_point := src/main.tsx:7 (createRoot → App).
  - critical_path := main.tsx → App.tsx → ChatView.tsx → useSession.ts (sessionId) → useChat.ts (send/sendVoice) → api.ts (sendChat) → chat-state.ts (chatReducer) → MessageList.tsx → UserMessage.tsx/BotMessage.tsx.
  - voice_subpath := PromptBar.tsx → useVoiceRecording.ts → useRecorder.ts (MediaRecorder) + useSpeechFallback.ts (Web Speech) → useChat.sendVoice() → api.ts sendChat (audio_file multipart).
  - leaf_files := { RecordButton.tsx, RecordingBar.tsx, VoiceBubble.tsx, EmotionDetail.tsx, SongCard.tsx, SongPlayerDialog.tsx, useSpeechFallback.ts, useRecorder.ts, api-types.gen.ts, main.tsx }.

## Behavior (input → process → output, 运行时视图)

- input: User text from PromptBar Textarea or voice from useVoiceRecording (Blob + transcriptHint string); sessionId from useSession (localStorage or new UUID); goal from GoalPicker state in ChatView [ChatView.tsx:49, PromptBar.tsx:69-75, useSession.ts:32-38, useChat.ts:41].
- process:
  1. ChatView calls useSession() → loadOrCreate() reads `SESSION_KEY` from localStorage or generates UUID [useSession.ts:60, useSession.ts:32-38].
  2. ChatView calls useChat(sessionId, goal) → useReducer(chatReducer, initialState(sessionId, loadLocal(sessionId))) [useChat.ts:42-44].
  3. On session change: load localStorage messages; if empty, call getSession(sessionId) → turnsToMessages → dispatch "hydrate" [useChat.ts:55-74, chat-state.ts:204-232].
  4. ChatView calls useMeta() → getMeta() (GET /api/meta) on mount + getHealth() (GET /api/health) every 30s [useMeta.ts:20-53, api.ts:105-109].
  5. User types + Enter → PromptBar.submit() → useChat.send(text) → dispatch "send" → deliver(id, text, goal) [PromptBar.tsx:69-75, useChat.ts:130-152].
  6. deliver() calls sendChat(): builds FormData (session_id, message?, goal?, audio_file?, transcript_hint?) → fetch POST /api/chat [useChat.ts:93-107, api.ts:60-82].
  7. On success: dispatch "resolve" → chatReducer updates user msg (status:sent, emotion) + pushes bot msg (reply, songs, safety, turnId) [chat-state.ts:108-138].
  8. On failure: dispatch "fail" → user msg status:error + errorText [chat-state.ts:148-156, useChat.ts:118-121].
  9. Voice: PromptBar.useVoiceRecording.start() → useRecorder.start() (getUserMedia + MediaRecorder) + useSpeechFallback.start() (Web Speech vi-VN) in parallel [useVoiceRecording.ts:34-43]. send() → stopRecorder() (blob) + stopSpeech() (transcriptHint) → onComplete → handleVoice → useChat.sendVoice(voice) [PromptBar.tsx:47-56, useChat.ts:154-181].
  10. sendVoice creates object URL for local playback, stores VoicePayload in voiceRef, dispatches "send" with voice, calls deliver() with audio {blob, filename} + transcriptHint [useChat.ts:163-177, useChat.ts:98-106].
  11. Bot reply rendered by BotMessage: useTypewriter for fresh messages, SongList for songs, SafetyAlert if safety=true, FeedbackButtons if turnId present [BotMessage.tsx:16-43].
  12. Emotion rendered by UserMessage: EmotionChip (popover → EmotionDetail progress bars) + ArousalChip, only when status=sent && emotion≠null [UserMessage.tsx:73-78].
  13. Aurora background: ChatView scans messages backward for last user emotion → sets `--mood` CSS var from emotionMeta(cssVar) [ChatView.tsx:112-122].
- output: ChatResponse {turn_id: string, reply: string, transcript?: string|null, emotion?: Emotion|null, songs?: Song[], safety: boolean, meta: Meta} consumed by chatReducer → ChatMessage[] rendered by MessageList [api-types.gen.ts:127-143, chat-state.ts:108-138, MessageList.tsx:40-52].
- side_effects: POST /api/chat (multipart FormData), GET /api/meta, GET /api/health (30s poll), GET /api/session/{id}, POST /api/feedback (JSON); localStorage reads/writes (SESSION_KEY, CONVERSATIONS_KEY, messagesKey); URL.createObjectURL for voice playback (revoked on session switch); MediaRecorder + getUserMedia (mic); Web Speech API recognition.

## Findings (cite file:line)

### (1) API client — src/lib/api.ts

- **API_BASE** = "/api" [api.ts:12]. All endpoints are relative (Vite proxy forwards to backend).
- **sendChat()** [api.ts:60-82]: builds `FormData` with `session_id` (always), `message` (if text), `goal` (if set), `audio_file` (blob + filename, if voice), `transcript_hint` (if Web Speech produced text). `fetch POST /api/chat` with FormData body (browser auto-sets multipart boundary). Returns `ChatResponse` JSON. Non-ok → `toApiError()`.
- **getMeta()** [api.ts:105-106]: `getJson<MetaResponse>("/meta")` → `fetch GET /api/meta` → JSON parse.
- **getHealth()** [api.ts:108-109]: `getJson<HealthResponse>("/health")` → `fetch GET /api/health` → JSON parse.
- **getSession()** [api.ts:111-112]: `getJson<SessionResponse>("/session/{id}")` — used by useChat for hydration.
- **sendFeedback()** [api.ts:86-103]: `POST /api/feedback` with JSON body {session_id, turn_id, rating}.
- **getJson<T>()** [api.ts:38-42]: generic GET wrapper; `fetch(API_BASE + path)` → `res.ok ? res.json() : throw toApiError(res)`.
- **toApiError()** [api.ts:25-36]: parses `{detail: string}` or `{detail: [{msg}]}` (FastAPI validation error) into human-readable string.
- **ApiError** [api.ts:14-23]: `extends Error` with `status: number` + `detail: string`.
- **Types** [api.ts:1-10]: re-exported from `api-types.gen.ts` (auto-generated via `openapi-typescript ../backend/openapi.json` [package.json:12]).

### (2) Data flow: useChat ← useSession ← ChatView

- **ChatView** [ChatView.tsx:40-165] is the top-level chat orchestrator:
  - Calls `useSession()` → `{sessionId, newSession, conversations, selectSession, recordConversation, deleteConversation}` [ChatView.tsx:41-48].
  - Calls `useChat(sessionId, goal)` → `{messages, pending, lastMeta, send, sendVoice, retry, rate, resetMeta}` [ChatView.tsx:50-59].
  - Calls `useMeta()` → `{meta, failed, modelServer}` [ChatView.tsx:60].
  - Derives `connection` status from `failed`/`meta` [ChatView.tsx:62-66].
  - Manages `goal` state locally (useState) [ChatView.tsx:49].
  - Records conversation to sidebar history when messages change [ChatView.tsx:99-102].
  - Computes aurora mood CSS from last user emotion [ChatView.tsx:112-122].

- **useChat** [useChat.ts:41-226]:
  - State: `useReducer(chatReducer, initialState(sessionId, loadLocal(sessionId)))` [useChat.ts:42-44].
  - `loadLocal()`: reads `messagesKey(sessionId)` from localStorage [useChat.ts:24-27].
  - Session switch effect: dispatch "switch", if local empty → `getSession(sessionId)` → `turnsToMessages` → dispatch "hydrate" [useChat.ts:55-74].
  - `deliver()` [useChat.ts:93-124]: core async — calls `sendChat()` with either voice payload (audio + transcriptHint) or text message; on success dispatches "resolve" (updates user msg + adds bot msg); on failure dispatches "fail".
  - `send()` [useChat.ts:130-152]: validates text, guards against concurrent sends, dispatches "send", calls `deliver()`.
  - `sendVoice()` [useChat.ts:154-181]: creates object URL, stores VoicePayload in ref map, dispatches "send" with voice metadata, calls `deliver()` with audio.
  - `retry()` [useChat.ts:183-191]: re-dispatches "retry" → "sending", re-calls `deliver()`.
  - `rate()` [useChat.ts:194-212]: optimistic update via dispatch "rate", calls `sendFeedback()`, reverts on error.
  - Persists messages to localStorage on every state change [useChat.ts:88-91].
  - Revokes object URLs on session switch/unmount [useChat.ts:77-85].

- **chat-state.ts** [chat-state.ts:1-232]:
  - `UserMessage` type: id, role, text, status (sending|sent|error), createdAt, goal, emotion, kind? ("voice"), audioUrl?, durationMs? [chat-state.ts:11-26].
  - `BotMessage` type: id, role, text, status:"sent", createdAt, songs[], safety, replyTo, turnId?, rating?, fresh? [chat-state.ts:28-43].
  - `chatReducer` [chat-state.ts:83-174]: handles 7 action types — "send" (append user msg), "resolve" (update user + append bot), "rate" (update bot rating), "fail" (user→error), "retry" (user→sending), "switch" (replace session+messages), "hydrate" (conditional restore).
  - `toStored()` [chat-state.ts:177-194]: strips `fresh` flag and `audioUrl` before localStorage persistence; keeps last 100 messages.
  - `turnsToMessages()` [chat-state.ts:204-232]: converts `SessionTurn[]` from backend to `ChatMessage[]` pairs (user+bot per turn).

### (3) Voice path: useRecorder + useVoiceRecording + useSpeechFallback

- **useVoiceRecording** [useVoiceRecording.ts:11-68]: composition layer.
  - Instantiates `useSpeechFallback()` and `useRecorder({onAutoStop})` [useVoiceRecording.ts:15, 22-26].
  - `start()` [useVoiceRecording.ts:34-43]: calls `startRecorder()` then `startSpeech()` (parallel).
  - `send()` [useVoiceRecording.ts:45-49]: `stopRecorder()` → blob result + `stopSpeech()` → transcriptHint → `onComplete({...result, transcriptHint})`.
  - `cancel()` [useVoiceRecording.ts:51-55]: cancels both recorder and speech.
  - Exposes: `{state, active, recording, elapsedMs, maxMs, liveText, start, send, cancel}` [useVoiceRecording.ts:57-68].

- **useRecorder** [useRecorder.ts:118-272]: MediaRecorder wrapper.
  - `MAX_RECORDING_MS = 30_000` (30s) [useRecorder.ts:3].
  - `TIMESLICE_MS = 250` [useRecorder.ts:4].
  - MIME candidates: `audio/webm;codecs=opus`, `audio/ogg;codecs=opus`, `audio/mp4` [useRecorder.ts:7-11].
  - `start()` [useRecorder.ts:211-264]: checks secure context + MediaRecorder support → `getUserMedia({audio: {echoCancellation, noiseSuppression}})` → `new MediaRecorder(stream, {mimeType})` → `recorder.start(250)` → starts elapsed timer (100ms tick) + max-duration timeout.
  - `stop()` [useRecorder.ts:266]: calls `finish()` → `recorder.onstop` → `new Blob(chunks, {type: mimeType})` → resolves `{blob, mimeType, durationMs}` [useRecorder.ts:156-188].
  - `cancel()` [useRecorder.ts:190-209]: stops recorder, clears chunks, releases stream.
  - `filenameFor()` [useRecorder.ts:61-68]: maps MIME to file extension (voice.ogg, voice.m4a, voice.wav, voice.webm).
  - Error classification: denied/no-device/unsupported/insecure/failed [useRecorder.ts:78-96].

- **useSpeechFallback** [useSpeechFallback.ts:54-134]: Web Speech API (vi-VN) parallel transcription.
  - `getRecognitionCtor()` [useSpeechFallback.ts:28-35]: checks `window.SpeechRecognition || window.webkitSpeechRecognition`.
  - `start()` [useSpeechFallback.ts:84-124]: creates Recognition, sets `lang="vi-VN"`, `continuous=true`, `interimResults=true`; accumulates final + interim transcripts; auto-restarts on Chrome timeout.
  - `stop()` [useSpeechFallback.ts:67-82]: stops recognition, returns accumulated text (trimmed).
  - Fatal errors (not-allowed, service-not-allowed, language-not-supported) → stop permanently [useSpeechFallback.ts:44-48, 105-107].
  - All errors swallowed — if unsupported, all functions are no-ops [useSpeechFallback.ts:52-53, 89].

- **Audio upload**: `useChat.sendVoice()` stores `{blob, filename, transcriptHint}` in `voiceRef` [useChat.ts:164-168]. `deliver()` calls `sendChat({sessionId, goal, audio: {blob, filename}, transcriptHint})` [useChat.ts:98-106]. `sendChat` appends `audio_file` (blob) to FormData [api.ts:72].

- **Playback**: `VoiceBubble` [VoiceBubble.tsx:16-88] plays the user's own local recording via `<audio src={audioUrl}>` (object URL created in `useChat.sendVoice()` [useChat.ts:163]). Play/Pause button toggles `audioRef.current.play()/pause()`. **No TTS** — there is no `SpeechSynthesis` API usage anywhere in the frontend (rg #2 for "SpeechSynthesis" returned 0 hits). `audioUrl` is not persisted to localStorage (stripped by `toStored()` [chat-state.ts:187-190]), so after page reload VoiceBubble shows a Mic icon instead of play button [VoiceBubble.tsx:66-73].

- **PromptBar integration** [PromptBar.tsx:37-139]:
  - `useVoiceRecording(handleVoice, handleVoiceError)` [PromptBar.tsx:60].
  - `handleVoice`: rejects recordings < 500ms as accidental tap [PromptBar.tsx:47-52].
  - When `voice.recording` → renders `RecordingBar` (timer + live transcript + cancel/send) [PromptBar.tsx:95-103].
  - When idle → renders `RecordButton` + `Textarea` + Send button [PromptBar.tsx:104-131].
  - Enter sends text (IME-safe: `!e.nativeEvent.isComposing`) [PromptBar.tsx:79].

### (4) Component structure

#### components/chat/

- **ChatView.tsx** [ChatView.tsx:40-165]: Orchestrator. Renders `SidebarProvider` (defaultOpen from cookie) → `AppSidebar` (conversation list) + `SidebarInset` (aurora background div + ChatHeader + MessageList/EmptyState + PromptBar).
- **ChatHeader.tsx** [ChatHeader.tsx:29-93]: Sticky header with bot avatar + connection dot (emerald/destructive/muted), title, status text, StatusBadge (mode/degraded/warnings/modelServer/llmBackend), ThemeToggle, new conversation button (hidden when sidebar visible).
- **MessageList.tsx** [MessageList.tsx:23-67]: `MessageScrollerProvider` → `MessageScroller` → maps ChatMessage[] to UserMessage/BotMessage; TypingIndicator when pending; scroll-to-bottom button.
- **UserMessage.tsx** [UserMessage.tsx:15-82]: Bubble (gradient for sent, destructive for error, opacity for sending); VoiceBubble for voice kind; EmotionChip + ArousalChip when sent+emotion; Spinner+“Đang gửi…” for sending; CircleAlert+retry button for error.
- **BotMessage.tsx** [BotMessage.tsx:16-43]: Bubble with typewriter effect (useTypewriter, only for fresh); SafetyAlert if safety=true; SongList for songs (hidden if safety); FeedbackButtons if turnId+onRate.
- **PromptBar.tsx** [PromptBar.tsx:37-139]: GoalPicker + RecordButton + Textarea + Send button (or RecordingBar when recording); IME-safe Enter; auto-grow textarea (max 160px).
- **RecordButton.tsx** [RecordButton.tsx:11-25]: Ghost button with Mic icon, aria-label, disabled/busy states.
- **RecordingBar.tsx** [RecordingBar.tsx:16-75]: Pulsing red dot + formatClock timer (elapsed/max), live transcript preview (line-clamp-2), cancel (X) + send (SendHorizontal) buttons.
- **VoiceBubble.tsx** [VoiceBubble.tsx:16-88]: Play/Pause local audio via `<audio>` object URL; duration display; transcript text or pending/fallback message.
- **AppSidebar.tsx**: Conversation history sidebar (imported at ChatView.tsx:11, not read in this session).
- **EmptyState.tsx**: Shown when messages.length===0 && !pending; onPick sends suggested text (ChatView.tsx:146, not read).
- **GoalPicker.tsx**: Goal selector dropdown in PromptBar (imported at PromptBar.tsx:18, not read).
- **FeedbackButtons.tsx**: Up/down rating buttons in BotMessage (imported at BotMessage.tsx:9, not read).
- **BotAvatar.tsx**: Bot avatar icon (imported at BotMessage.tsx:8, not read).
- **TypingIndicator.tsx**: Animated typing dots (imported at MessageList.tsx:13, not read).

#### components/music/

- **SongList.tsx** [SongList.tsx:6-29]: Container. Empty → null. Renders `<ul>` with horizontal snap-scroll on mobile, CSS grid (auto-fill, minmax 12rem) on desktop. Each song → SongCard. Manages `playing` state (index) for SongPlayerDialog.
- **SongCard.tsx** [SongCard.tsx:25-113]: Card with 16:9 AspectRatio thumbnail (YouTube thumbnail via `thumbnailUrl(id)`, fallback gradient with Music icon if image fails or is 120x90 placeholder). Play button (if YouTube ID) opens dialog; external link if no ID. Title (truncate), artist (truncate), reason (line-clamp-2), “Mở trên YouTube” link.
- **SongPlayerDialog.tsx** [SongPlayerDialog.tsx:52-213]: Dialog with YouTube `<iframe>` embed (`embedUrl(id)`). Prev/next navigation (ArrowLeft/ArrowRight keyboard support). Position counter (pos+1/playable.length). Strip thumbnail playlist at bottom. “Mở trên YouTube” external link + close button.

#### components/emotion/

- **EmotionChip.tsx** [EmotionChip.tsx:21-45]: Popover-triggered badge button. Shows emotion icon + Vietnamese label + percentage. `emotionStyle()` applies CSS var color + 12% background. PopoverContent renders EmotionDetail. Also exports `ArousalChip` [EmotionChip.tsx:47-57]: Badge with Activity icon + arousal label (low/medium/high in Vietnamese).
- **EmotionDetail.tsx** [EmotionDetail.tsx:6-45]: Popover content. Maps `EMOTION_LABELS` to sorted rows (descending probability). Each row: icon (colored), Vietnamese label, Progress bar (CSS var colored), percentage. Footer: “Kết quả máy đoán, có thể sai”.

### (5) App.tsx top-level layout and state providers

- **App.tsx** [App.tsx:6-15]:
  ```
  <ThemeProvider>
    <TooltipProvider>
      <ChatView />
      <Toaster position="top-center" />
    </TooltipProvider>
  </ThemeProvider>
  ```
  - `ThemeProvider` [theme-provider.tsx, imported at App.tsx:2]: wraps next-themes for dark/light switching.
  - `TooltipProvider` [ui/tooltip.tsx, imported at App.tsx:4]: Radix UI tooltip context.
  - `ChatView`: the entire chat UI (sidebar + header + messages + input).
  - `Toaster` [ui/sonner.tsx, imported at App.tsx:3]: sonner toast notifications (top-center).

- **main.tsx** [main.tsx:7-11]: `createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>)`.

- **State providers summary**: No Redux or Context beyond ThemeProvider (theme) and TooltipProvider (tooltips). Chat state is local to ChatView via hooks (useSession, useChat, useMeta) — not lifted to a global provider. Session ID and conversations persist in localStorage via `src/lib/storage.ts`.

## Next reads (若 scope 对消费者不足)

- 关于 backend /api/chat handler implementation → `../backend/` (not in frontend scope).
- 关于 useTypewriter animation internals → src/hooks/useTypewriter.ts:1.
- 关于 theme-provider switching → src/components/theme-provider.tsx.
- 关于 localStorage key scheme → src/lib/storage.ts.
- 关于 AppSidebar conversation list rendering → src/components/chat/AppSidebar.tsx.
- 关于 emotion label/icon/cssVar mapping → src/lib/emotion-meta.ts.
- 关于 goal definitions → src/lib/goals.ts.
- 关于 YouTube URL parsing (extractVideoId, thumbnailUrl, embedUrl, watchUrl) → src/lib/youtube.ts.
- 关于 SafetyAlert/StatusBadge rendering → src/components/system/SafetyAlert.tsx, src/components/system/StatusBadge.tsx.
- 关于 EmptyState suggested prompts → src/components/chat/EmptyState.tsx.

## Gherkin scenarios (≥ 1 when applicable)

```gherkin
Feature: Frontend chat flow end-to-end
  Scenario: User sends text message
    Given ChatView is mounted with sessionId from useSession
    And useChat has initialized chatReducer with localStorage messages
    When user types "tôi buồn" in PromptBar Textarea and presses Enter
    Then useChat.send("tôi buồn") dispatches "send" action
    And deliver() calls sendChat({sessionId, message: "tôi buồn", goal})
    And fetch POST /api/chat with FormData{session_id, message, goal}
    And on 200: chatReducer dispatches "resolve" → user msg status=sent + bot msg with reply/songs/emotion
    And MessageList renders UserMessage (with EmotionChip if emotion) + BotMessage (with SongList)

  Scenario: User sends voice message
    Given PromptBar has instantiated useVoiceRecording(handleVoice, handleVoiceError)
    When user clicks RecordButton → useVoiceRecording.start()
    Then useRecorder.start() calls getUserMedia + MediaRecorder.start(250ms timeslice)
    And useSpeechFallback.start() starts Web Speech recognition (vi-VN) in parallel
    And RecordingBar shows timer + liveText from speech recognition
    When user clicks send → useVoiceRecording.send()
    Then stopRecorder() produces {blob, mimeType, durationMs}
    And stopSpeech() returns transcriptHint string
    And handleVoice receives VoiceRecording → useChat.sendVoice(voice)
    And sendChat({sessionId, goal, audio: {blob, filename}, transcriptHint})
    And fetch POST /api/chat FormData{session_id, audio_file, transcript_hint, goal}
    And on resolve: user msg updated with server transcript, VoiceBubble plays local recording

  Scenario: Frontend polls health endpoint
    Given useMeta is mounted in ChatView
    Then getMeta() fetches GET /api/meta on mount
    And getHealth() fetches GET /api/health immediately
    And getHealth() repeats every 30 seconds (HEALTH_POLL_MS)
    And polling pauses when document.visibilityState === "hidden"
    And modelServer status (up|down|n/a) displayed in ChatHeader via StatusBadge

  Scenario: No TTS in frontend
    When searching for "SpeechSynthesis" in frontend/src
    Then 0 matches found (rg confirmed)
    And VoiceBubble only replays user's own recording via <audio> element
    And bot replies are displayed as text (with typewriter effect), never spoken aloud
```
