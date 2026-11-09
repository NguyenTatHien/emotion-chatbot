# Emotion Chatbot

Chatbot tiếng Việt nhận tin nhắn văn bản hoặc giọng nói, nhận diện cảm xúc người dùng, trả lời theo hướng đồng cảm và gợi ý 3–5 bài hát phù hợp. Đồ án cuối kỳ môn NLP501.

> Đây **không phải** công cụ chẩn đoán tâm lý. Khi phát hiện dấu hiệu tự làm hại, hệ thống chuyển sang thông điệp an toàn.

## Trạng thái

Khung backend (FastAPI), giao diện chat (React), nhập giọng nói, chế độ `remote` gọi model server trên Colab, chuỗi dự phòng LLM (Qwen → Gemini → câu soạn sẵn) và nút đánh giá đã chạy được; toàn bộ vẫn chạy được bằng mock. Docker sẽ được thêm theo kế hoạch 5 ngày.

## Luồng xử lý một lượt chat

```
Người dùng ──▶ Frontend (React) ──POST /api/chat──▶ Backend (FastAPI)
                                                       │
            ghi âm ──▶ chuẩn hoá WAV 16 kHz ──▶ transcribe() + extract_prosody()
                                                       │
                     văn bản ──▶ check_safety() ──▶ có rủi ro? ──▶ thông điệp an toàn
                                                       │ không
                                              predict_emotion()  (CafeBERT, 7 nhãn)
                                                       │
                              generate_reply()  ║  recommend()   (chạy song song)
                                                       │
                                     JSON: reply, transcript, emotion, songs, meta
```

## Công nghệ

| Lớp | Công nghệ |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2, httpx, ffmpeg |
| Frontend | React + Vite + TypeScript, Tailwind CSS v4, shadcn/ui |
| Mô hình | CafeBERT (`BaoNhan/cafebert-UITVSMEC`), PhoWhisper, Qwen3-4B / Gemini API, librosa |
| Hạ tầng | Docker Compose; mô hình chạy trên Colab T4 qua tunnel |

## Cấu trúc dự kiến

```
emotion-chatbot/
├── backend/            # FastAPI, pipeline, registry, mocks
│   └── modules/        # mỗi file = một hợp đồng hàm, do từng thành viên viết ruột
├── frontend/           # React + shadcn/ui
├── colab/              # khung model server (FastAPI) + hướng dẫn chạy trên Colab
├── notebooks/          # đánh giá E1–E4
└── docker-compose.yml
```

## Hợp đồng module

Mỗi file trong `backend/modules/` chỉ export đúng một hàm theo chữ ký đã chốt. Module được coi là xong khi qua contract test tương ứng:

```bash
pytest tests/contract -k <tên_module>
```

| Module | Hàm | Phụ trách |
|---|---|---|
| `emotion.py` | `predict_emotion(text)` | Người 1 |
| `speech.py` | `transcribe(wav_path)`, `extract_prosody(wav_path)` | Người 3 |
| `safety.py` | `check_safety(text)` | Người 3 |
| `llm.py` | `generate_reply(text, emotion, arousal, history, goal)` | Người 3 |
| `music.py` | `recommend(label, arousal, goal, k)` | Người 5 |
| Backend, frontend, Docker | | Hiển (Người 4) |

## Chạy backend

Yêu cầu: [uv](https://docs.astral.sh/uv/). Từ thư mục `backend/`:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt   # Windows
# Linux/macOS: uv pip install --python .venv/bin/python -r requirements-dev.txt
cp .env.example .env            # tùy chọn; mặc định chạy mock
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --workers 1
```

> Luôn chạy `--workers 1`: bộ nhớ phiên nằm trong RAM của tiến trình.

Thử nhanh:

```bash
curl -F session_id=s1 -F message="hôm nay mệt quá" http://127.0.0.1:8000/api/chat
```

Kiểm tra: `ruff check .` và `pytest -q` trong `backend/`. Tài liệu API tương tác tại `http://127.0.0.1:8000/docs`; file `backend/openapi.json` dùng để sinh kiểu TypeScript cho frontend (`python -m app.tools.export_openapi`).

### Route

| Route | Mô tả |
|---|---|
| `POST /api/chat` | Form: `session_id` (bắt buộc), `message`, `audio_file`, `transcript_hint`, `goal` (`xoa_diu`, `nang_mood`, `tap_trung`, `giai_toa`) |
| `GET /api/health` | `{ok, model_server}`; `model_server` là `up`/`down` (gọi thật `GET {MODEL_SERVER_URL}/health`, timeout 3 s, cache 10 s) hoặc `n/a` khi không có module remote |
| `POST /api/feedback` | JSON `{session_id, turn_id, rating}` (`up`/`down`); 404 nếu lượt không có trong phiên |
| `GET /api/feedback/export` | CSV đánh giá mới nhất theo `turn_id`; cần `Authorization: Bearer <ADMIN_TOKEN>` |
| `GET /api/meta` | Nhãn cảm xúc, goal, mode từng module |
| `GET /api/session/{session_id}` | Lịch sử các lượt của phiên |

### Biến môi trường chính

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MODEL_MODE` | `mock` | Mode chung cho mọi module: `mock` \| `local` \| `remote` |
| `EMOTION_MODE`, `SPEECH_MODE`, `SAFETY_MODE`, `LLM_MODE`, `MUSIC_MODE` | trống | Ghi đè mode cho từng module |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Origin được phép gọi API |
| `HISTORY_TURNS` | `6` | Số lượt gần nhất truyền cho LLM |
| `MOCK_LATENCY_MS` | `0` | Giả độ trễ cho mock |
| `SAFETY_HOTLINE_TEXT` | trống | Dòng hỗ trợ thêm vào thông điệp an toàn |
| `MODEL_SERVER_URL`, `MODEL_SERVER_TOKEN` | trống | URL và bí mật dùng chung của model server (bắt buộc URL khi có module remote) |
| `REMOTE_TIMEOUT_EMOTION/TRANSCRIBE/PROSODY/GENERATE` | `10/20/10/30` | Timeout (giây) từng lời gọi tới model server |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | trống, `gemini-3.6-flash` | Dự phòng Gemini; trống khoá = bỏ bước này |
| `FEEDBACK_PATH`, `ADMIN_TOKEN` | `data/feedback.jsonl`, trống | File đánh giá; trống `ADMIN_TOKEN` = route export trả 404 |

| `MAX_AUDIO_SECONDS`, `MAX_AUDIO_MB` | `30`, `5` | Giới hạn bản ghi; vượt thì trả HTTP 413 |
| `FFMPEG_BINARY` | `ffmpeg` | Tên hoặc đường dẫn ffmpeg dùng để chuẩn hoá audio |

### Giọng nói

- **Cần ffmpeg** khi chạy backend không dùng Docker: backend chuẩn hoá mọi định dạng trình duyệt gửi (webm/opus, ogg, mp4/aac, wav) sang WAV 16 kHz mono trước khi gọi `speech.py`. Cài ffmpeg (`winget install ffmpeg`, `brew install ffmpeg` hoặc `apt install ffmpeg`) rồi đảm bảo có trên `PATH`, hoặc đặt `FFMPEG_BINARY`. Nếu không thấy, backend thử gói `imageio-ffmpeg` (chỉ có trong `requirements-dev.txt`, dùng cho test/dev); vẫn không có thì bước speech được coi là lỗi và hệ thống dùng chữ nhận dạng sẵn từ trình duyệt (`transcript_hint`), không trả 500. Image Docker (change sau) phải cài ffmpeg bằng apt.
- Mã lỗi: `413` khi file quá `MAX_AUDIO_MB` hoặc dài hơn `MAX_AUDIO_SECONDS` + 1 giây, `415` khi ffmpeg không giải mã được, `400` khi không nhận dạng được chữ nào và không có `message`/`transcript_hint`.
- Test tự sinh audio mẫu bằng ffmpeg, không commit file nhị phân.

### Mode remote (model server trên Colab)

Đặt `EMOTION_MODE`, `SPEECH_MODE`, `LLM_MODE` thành `remote` cùng `MODEL_SERVER_URL` (và `MODEL_SERVER_TOKEN` nếu server đặt token). Backend gọi `POST /emotion`, `/transcribe`, `/prosody`, `/generate` bằng httpx async, gửi header `X-Model-Server-Token`. Timeout, lỗi kết nối, HTTP lỗi hoặc phản hồi sai schema đều được coi là module lỗi: `POST /api/chat` vẫn trả 200 với `meta.degraded=true`. `SAFETY_MODE=remote` và `MUSIC_MODE=remote` bị từ chối khi khởi động (hai module này luôn chạy trong backend), cũng như khi thiếu `MODEL_SERVER_URL`. Khung server và hướng dẫn Colab/ngrok: [colab/README.md](colab/README.md).

### Chuỗi dự phòng LLM

Thứ tự: implementation `llm` theo mode → Gemini (nếu có `GEMINI_API_KEY`) → câu soạn sẵn theo nhãn. `meta.llm_backend` là nguồn thực sự đã trả lời: `mock`, `qwen`, `gemini` hoặc `canned`; mỗi bước hỏng thêm một cảnh báo vào `meta.warnings` và đặt `degraded=true`. Gemini được gọi qua REST `generateContent` (không dùng SDK), khoá chỉ nằm trong header `x-goog-api-key` và không bao giờ xuất hiện trong log hay phản hồi.

Model mặc định `gemini-3.6-flash` là model "Stable" dòng Flash trong danh sách model của Google AI tại <https://ai.google.dev/gemini-api/docs/models> (trang chuyển hướng tới <https://aistudio.google.com/docs/models>), kiểm tra ngày 10/11/2026. Muốn đổi model chỉ cần sửa `GEMINI_MODEL`; lỗi tên model chỉ làm rơi xuống câu soạn sẵn.

### Đánh giá của người dùng thử (cho Người 5)

Dưới mỗi câu trả lời của bot (trừ lượt an toàn) có nút "Hữu ích"/"Chưa hợp". Mỗi lần bấm ghi thêm một dòng JSONL vào `FEEDBACK_PATH` gồm `session_id, turn_id, rating, emotion_label, arousal, goal, safety, llm_backend, created_at` — **không lưu nội dung tin nhắn hay câu trả lời**. Đổi đánh giá cho cùng lượt thì dòng mới thắng. Xuất CSV (mới nhất theo `turn_id`):

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/api/feedback/export -o feedback.csv
```

Cần đặt `ADMIN_TOKEN` trong `.env`; để trống thì route trả 404. File dữ liệu được `.gitignore` bỏ qua; khi triển khai Docker hãy mount volume cho thư mục chứa nó.

Danh sách đầy đủ kèm chú thích: `backend/.env.example`. Hướng dẫn cắm module thật: [CONTRIBUTING.md](CONTRIBUTING.md).

## Chạy frontend

Yêu cầu: Node 22+ và pnpm. Chạy backend trước (xem trên), rồi từ thư mục `frontend/`:

```bash
pnpm install
pnpm dev            # http://localhost:5173, proxy /api -> http://127.0.0.1:8000
```

| Lệnh | Việc |
|---|---|
| `pnpm lint` | ESLint |
| `pnpm test` | Vitest + Testing Library (jsdom) |
| `pnpm build` | `tsc -b` + build production vào `dist/` |
| `pnpm gen:types` | Sinh `src/lib/api-types.gen.ts` từ `backend/openapi.json` (chạy lại sau khi đổi API) |

Ghi chú kỹ thuật:

- Khởi tạo bằng `shadcn` CLI **4.23.0** (`pnpm dlx shadcn@latest init -t vite -b radix -p nova`), style `radix-nova`, base Radix. Component shadcn nằm ở `src/components/ui/` (không sửa tay); phần tuỳ biến nằm ở `src/components/{chat,emotion,music,system}/`. Các component `message`, `message-scroller`, `bubble` phụ thuộc gói `@shadcn/react`.
- Không dùng Vercel AI SDK; state chat tự quản bằng `useReducer` (`src/hooks/chat-state.ts`, `useChat.ts`). Gọi API bằng `fetch` với đường dẫn tương đối `/api`.
- Font Be Vietnam Pro tự host qua `@fontsource` (không gọi Google Fonts). Màu chủ đạo violet-600; 7 màu cảm xúc là biến CSS `--emo-*` trong `src/index.css` (light/dark).
- Phiên: `session_id` và tin nhắn lưu trong localStorage (`ec.session_id`, `ec.messages.<id>`); nếu localStorage trống thì khôi phục từ `GET /api/session/{id}`.
- Ghi âm: `useRecorder` (MediaRecorder, tự chọn `audio/webm;codecs=opus` > `audio/ogg;codecs=opus` > `audio/mp4`, tự dừng ở 30 giây), `useSpeechFallback` (Web Speech API `vi-VN`, chạy song song để hiện chữ trực tiếp và gửi `transcript_hint`), `RecordingBar`, `VoiceBubble`. Bản ghi để phát lại chỉ nằm trong RAM của tab (object URL, thu hồi khi bắt đầu cuộc trò chuyện mới) và không lưu vào localStorage.
- **Ghi âm cần `localhost` hoặc HTTPS** (secure context); mở bằng địa chỉ IP qua HTTP thì trình duyệt chặn micro và giao diện hiện thông báo, ô gõ chữ vẫn dùng bình thường.
- **Quyền riêng tư**: Web Speech API trên Chrome/Edge gửi âm thanh tới dịch vụ nhận dạng của hãng trình duyệt (Google/Microsoft). Nó chỉ là dự phòng hiển thị chữ trực tiếp; nguồn chính là PhoWhisper chạy ở backend của nhóm. Hãy nói rõ điều này với người dùng khi demo.

## Giới hạn

- UIT-VSMEC là bình luận mạng xã hội, lệch miền so với lời tâm sự.
- Không phân loại cảm xúc từ giọng nói; tông giọng chỉ là tín hiệu phụ (mức kích động).
- Không tuyên bố độ chính xác đa phương thức.
