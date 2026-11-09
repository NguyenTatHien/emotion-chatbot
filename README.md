# Emotion Chatbot

Chatbot tiếng Việt nhận tin nhắn văn bản hoặc giọng nói, nhận diện cảm xúc người dùng, trả lời theo hướng đồng cảm và gợi ý 3–5 bài hát phù hợp. Đồ án cuối kỳ môn NLP501.

> Đây **không phải** công cụ chẩn đoán tâm lý. Khi phát hiện dấu hiệu tự làm hại, hệ thống chuyển sang thông điệp an toàn.

## Trạng thái

Khung backend (FastAPI) và giao diện chat (React) đã chạy được hoàn toàn bằng mock. Voice, tích hợp mô hình thật và Docker sẽ được thêm theo kế hoạch 5 ngày.

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
├── colab/              # notebook model server
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
| `GET /api/health` | `{ok, model_server}` |
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
- Chỗ chừa cho nút ghi âm: prop `voiceSlot` của `PromptBar` (change `add-voice-input`).

## Giới hạn

- UIT-VSMEC là bình luận mạng xã hội, lệch miền so với lời tâm sự.
- Không phân loại cảm xúc từ giọng nói; tông giọng chỉ là tín hiệu phụ (mức kích động).
- Không tuyên bố độ chính xác đa phương thức.
