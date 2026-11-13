# Emotion Chatbot

[![CI](https://github.com/NguyenTatHien/emotion-chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/NguyenTatHien/emotion-chatbot/actions/workflows/ci.yml)

Chatbot tiếng Việt nhận tin nhắn văn bản hoặc giọng nói, nhận diện cảm xúc người dùng, trả lời theo hướng đồng cảm và gợi ý 3–5 bài hát phù hợp. Đồ án cuối kỳ môn NLP501.

> Đây **không phải** công cụ chẩn đoán tâm lý. Khi phát hiện dấu hiệu tự làm hại, hệ thống chuyển sang thông điệp an toàn.

## Trạng thái

Khung backend (FastAPI), giao diện chat (React), nhập giọng nói, chế độ `remote` gọi model server trên Colab, chuỗi dự phòng LLM (Qwen → Gemini → câu soạn sẵn) và nút đánh giá đã chạy được; toàn bộ vẫn chạy được bằng mock. Đã có Docker (chạy local, dev có hot reload), CI GitHub Actions và cấu hình triển khai lên server.

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
                              late fusion: arousal của giọng điều chỉnh xác suất
                                                       │
                    generate_reply()  (câu trả lời mở đầu bằng thẻ [NHAC:CO|KHONG])
                                                       │
                       có chip mục tiêu hoặc thẻ CO? ──▶ recommend()
                       (chip: chạy song song với generate_reply; thẻ: chạy sau)
                                                       │
                                     JSON: reply, transcript, emotion, songs, meta
```

### Gợi ý nhạc theo ngữ cảnh

Không phải lượt nào cũng có bài hát. Thứ tự quyết định, dừng ở bước đầu tiên khớp (kết quả nằm ở `meta.music_decision`):

1. Safety báo rủi ro → không nhạc (`safety`).
2. Người dùng bấm chip mục tiêu (`goal`) → luôn có nhạc (`chip`); LLM và `recommend()` chạy song song.
3. Còn lại do LLM quyết bằng **thẻ ở dòng đầu** câu trả lời: `[NHAC:CO]` → có nhạc (`llm`), `[NHAC:KHONG]` → không (`llm_no`); `recommend()` chỉ được gọi sau khi có `CO`.
4. Không có thẻ (LLM quên, LLM lỗi, câu soạn sẵn) → không nhạc (`no_tag`).

Backend tách mọi thẻ (có hoặc không dấu, hoa hoặc thường, ở bất kỳ vị trí nào; thẻ đầu tiên quyết định) khỏi câu trả lời trước khi trả về, lưu phiên hay đưa vào lịch sử; thẻ chỉ được đọc từ câu trả lời của LLM, không từ tin nhắn người dùng. Nguồn chỉ trả đúng một thẻ thì bị coi là rỗng và chuyển sang nguồn kế tiếp. Vì vậy `songs` rỗng là kết quả bình thường của `POST /api/chat`.

Mock LLM gắn thẻ tất định (chỉ để dev/test): `CO` khi chữ có `nghe nhạc`, `bài hát`, `bài nào`, `playlist`, `mở nhạc`, hoặc khi nhãn là Sadness/Fear và đã có ít nhất một tin của người dùng trong lịch sử; còn lại là `KHONG`.

### Bộ nhớ hội thoại

Mỗi `session_id` có bộ nhớ riêng trong RAM (mất khi restart). `history` backend gửi cho `generate_reply` gồm:

- một **cặp tin bối cảnh** (user bắt đầu bằng `[BỐI CẢNH CUỘC TRÒ CHUYỆN` + assistant "Mình nhớ rồi."), chỉ khi có bản tóm tắt hoặc từng gợi ý nhạc: chứa bản tóm tắt và **hồ sơ nhạc** (tối đa 5 lượt gần nhất có bài, kèm "thích"/"không thích" từ `POST /api/feedback`);
- mọi lượt chưa được tóm tắt, nguyên văn, tối đa `HISTORY_TURNS + 2 × SUMMARY_BATCH_TURNS` lượt gần nhất.

Khi số lượt chưa tóm tắt đạt `HISTORY_TURNS + SUMMARY_BATCH_TURNS` và có `GEMINI_API_KEY`, backend tóm tắt `SUMMARY_BATCH_TURNS` lượt cũ nhất bằng Gemini **ở nền** (sau khi đã trả lời; không chặn response). Lượt có cảnh báo an toàn chỉ vào tóm tắt dưới dạng một câu trung tính. Tóm tắt lỗi, quá `SUMMARY_TIMEOUT` hoặc phiên đã bị xoá thì chỉ ghi log và giữ bản cũ. Không có khoá Gemini thì không có tóm tắt: bot vẫn có hồ sơ nhạc và các lượt gần nguyên văn.

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
├── deploy/             # compose production, deploy.sh, hướng dẫn triển khai
├── .github/workflows/  # ci.yml (kiểm thử), images.yml (build + đẩy image GHCR)
├── docker-compose.yml      # chạy local (cổng 8080)
└── docker-compose.dev.yml  # dev có hot reload
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

## Chạy bằng Docker

Yêu cầu: Docker Desktop (hoặc Docker Engine + Compose v2). Từ gốc repo:

```bash
docker compose up --build        # http://localhost:8080
docker compose down              # dừng và xóa container
```

- `web` (Caddy) phục vụ giao diện và chuyển `/api/*` tới `backend` trong mạng nội bộ; `backend` không mở cổng ra ngoài. Body gửi lên `/api` bị giới hạn 6 MB (vượt thì trả 413).
- `backend` đọc `backend/.env` nếu có (mặc định chạy mock). Image backend target `base` có ffmpeg nhưng **không** có torch; target `ml` (thêm torch CPU, transformers, librosa) dùng cho mode `local`: `docker build --target ml backend`.
- Trên Windows nếu `http://localhost:8080` không phản hồi từ một số công cụ dòng lệnh, dùng `http://127.0.0.1:8080`.

Chế độ dev có hot reload (backend `--reload`, Vite dev server):

```bash
docker compose -f docker-compose.dev.yml up --build   # giao diện http://localhost:5173, API http://localhost:8000
```

Mã nguồn được mount vào container và bật polling để nhận thay đổi trên Windows; Vite proxy `/api` tới `backend:8000` qua biến `VITE_API_PROXY` (mặc định `http://127.0.0.1:8000` khi chạy `pnpm dev` ngoài Docker).

## Kiến trúc triển khai

```
push main ─▶ images.yml ─▶ ghcr.io/nguyentathien/emotion-chatbot-{api,web}:sha-<7>/latest
         └─▶ deploy.yml (SSH key bị khoá, chỉ chạy remote-deploy.sh) ─▶ docker compose pull + up
Internet ─▶ javis-proxy (HTTPS) ─▶ web (Caddy) ─▶ backend (FastAPI)      trên realestate-vm
```

CI (`ci.yml`) chạy `ruff` + `pytest` cho backend và `pnpm lint` + `pnpm test` + `pnpm build` cho frontend trên mọi pull request và push `main`. Sau khi `images.yml` xong, `deploy.yml` tự triển khai lên https://emotion.hiennguyen.io.vn và kiểm tra `/api/health`. Server chỉ `pull` image build sẵn, chạy sau reverse proxy dùng chung với giới hạn bộ nhớ. Cấu hình secrets, deploy tay, rollback và gỡ bỏ: xem [deploy/README.md](deploy/README.md).

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
| `GET /api/session/{session_id}` | Lịch sử các lượt của phiên, mỗi lượt có `music_decision` và `rating` (`null` nếu chưa đánh giá) |

### Biến môi trường chính

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MODEL_MODE` | `mock` | Mode chung cho mọi module: `mock` \| `local` \| `remote` |
| `EMOTION_MODE`, `SPEECH_MODE`, `SAFETY_MODE`, `LLM_MODE`, `MUSIC_MODE` | trống | Ghi đè mode cho từng module; riêng `LLM_MODE` nhận thêm `gemini` |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Origin được phép gọi API |
| `HISTORY_TURNS` | `6` | Số lượt gần nhất giữ nguyên văn; cũng là mốc để bắt đầu tóm tắt các lượt cũ |
| `SUMMARY_BATCH_TURNS` | `4` | Số lượt cũ nhất gộp vào bản tóm tắt mỗi lần (tóm tắt khi chưa tóm tắt ≥ `HISTORY_TURNS + SUMMARY_BATCH_TURNS`) |
| `SUMMARY_MAX_WORDS` | `120` | Độ dài tối đa của bản tóm tắt (từ) |
| `SUMMARY_TIMEOUT` | `20` | Timeout lần tóm tắt nền bằng Gemini (giây) |
| `FUSION_ALPHA` | `0.2` | Hệ số late fusion giọng–chữ, trong [0, 0.5]; `0` = tắt (xem mục Late fusion) |
| `MOCK_LATENCY_MS` | `0` | Giả độ trễ cho mock |
| `SAFETY_HOTLINE_TEXT` | trống | Dòng hỗ trợ thêm vào thông điệp an toàn |
| `MODEL_SERVER_URL`, `MODEL_SERVER_TOKEN` | trống | URL và bí mật dùng chung của model server (bắt buộc URL khi có module remote) |
| `REMOTE_TIMEOUT_EMOTION/TRANSCRIBE/PROSODY/GENERATE` | `10/20/10/30` | Timeout (giây) từng lời gọi tới model server |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | trống, `gemini-3.5-flash-lite` | Nguồn chính khi `LLM_MODE=gemini`, dự phòng khi Qwen lỗi; trống khoá = bỏ bước này |
| `FEEDBACK_PATH`, `ADMIN_TOKEN` | `data/runtime/feedback.jsonl`, trống | File đánh giá; trống `ADMIN_TOKEN` = route export trả 404 |

| `MAX_AUDIO_SECONDS`, `MAX_AUDIO_MB` | `30`, `5` | Giới hạn bản ghi; vượt thì trả HTTP 413 |
| `FFMPEG_BINARY` | `ffmpeg` | Tên hoặc đường dẫn ffmpeg dùng để chuẩn hoá audio |

### Giọng nói

- **Cần ffmpeg** khi chạy backend không dùng Docker: backend chuẩn hoá mọi định dạng trình duyệt gửi (webm/opus, ogg, mp4/aac, wav) sang WAV 16 kHz mono trước khi gọi `speech.py`. Cài ffmpeg (`winget install ffmpeg`, `brew install ffmpeg` hoặc `apt install ffmpeg`) rồi đảm bảo có trên `PATH`, hoặc đặt `FFMPEG_BINARY`. Nếu không thấy, backend thử gói `imageio-ffmpeg` (chỉ có trong `requirements-dev.txt`, dùng cho test/dev); vẫn không có thì bước speech được coi là lỗi và hệ thống dùng chữ nhận dạng sẵn từ trình duyệt (`transcript_hint`), không trả 500. Image Docker đã cài ffmpeg bằng apt.
- Mã lỗi: `413` khi file quá `MAX_AUDIO_MB` hoặc dài hơn `MAX_AUDIO_SECONDS` + 1 giây, `415` khi ffmpeg không giải mã được, `400` khi không nhận dạng được chữ nào và không có `message`/`transcript_hint`.
- Test tự sinh audio mẫu bằng ffmpeg, không commit file nhị phân.

### Late fusion (giọng điều chỉnh cảm xúc)

- Theo mô hình valence–arousal của Russell: chữ quyết định valence, giọng (`arousal` = `low`/`high`) điều chỉnh xác suất. Nhóm năng lượng cao: Anger, Fear, Surprise, Enjoyment; nhóm thấp: Sadness, Other; Disgust giữ nguyên.
- Công thức: giọng `high` nhân nhóm cao với `1 + α`, nhóm thấp với `1 − α` (giọng `low` thì ngược lại), rồi chuẩn hoá để tổng bằng 1; nhãn cuối là argmax, hoà thì giữ nhãn từ chữ. `α = FUSION_ALPHA`.
- Chỉ áp dụng khi `arousal` là `low`/`high`, cảm xúc đến từ module thật (không phải dự phòng), `FUSION_ALPHA > 0` và lượt không có rủi ro an toàn. Gõ chữ, giọng `medium` hoặc prosody lỗi thì giữ nguyên kết quả từ chữ.
- Nhãn và xác suất sau khi kết hợp đi xuống LLM, music, session, bộ nhớ hội thoại và giao diện. Khi có fusion, `emotion.label_text` / `emotion.probs_text` giữ kết quả chỉ từ chữ và `meta.fusion_applied = true`.
- Đây là luật theo lý thuyết valence–arousal, α đặt tay và chưa có số đo độ chính xác. Tắt bằng `FUSION_ALPHA=0` mà không cần đổi code.

### Mode remote (model server trên Colab)

Đặt `EMOTION_MODE`, `SPEECH_MODE`, `LLM_MODE` thành `remote` cùng `MODEL_SERVER_URL` (và `MODEL_SERVER_TOKEN` nếu server đặt token). Backend gọi `POST /emotion`, `/transcribe`, `/prosody`, `/generate` bằng httpx async, gửi header `X-Model-Server-Token`. Timeout, lỗi kết nối, HTTP lỗi hoặc phản hồi sai schema đều được coi là module lỗi: `POST /api/chat` vẫn trả 200 với `meta.degraded=true`. `SAFETY_MODE=remote` và `MUSIC_MODE=remote` bị từ chối khi khởi động (hai module này luôn chạy trong backend), cũng như khi thiếu `MODEL_SERVER_URL`. Khung server và hướng dẫn Colab/ngrok: [colab/README.md](colab/README.md).

### Chuỗi dự phòng LLM

Thứ tự: implementation `llm` theo mode → Gemini (nếu có `GEMINI_API_KEY`) → câu soạn sẵn theo nhãn. Với `LLM_MODE=gemini`, Gemini là nguồn chính (`llm_backend=gemini`, không bị tính là dự phòng) và lỗi thì rơi thẳng xuống câu soạn sẵn; khởi động sẽ báo lỗi nếu thiếu `GEMINI_API_KEY`. `meta.llm_backend` là nguồn thực sự đã trả lời: `mock`, `qwen`, `gemini` hoặc `canned`; mỗi bước hỏng thêm một cảnh báo vào `meta.warnings` và đặt `degraded=true`. Gemini được gọi qua REST `generateContent` (không dùng SDK), khoá chỉ nằm trong header `x-goog-api-key` và không bao giờ xuất hiện trong log hay phản hồi.

Model mặc định `gemini-3.5-flash-lite` (dòng Flash-Lite trong danh sách model của Google AI tại <https://ai.google.dev/gemini-api/docs/models>, kiểm tra ngày 10/11/2026) được chọn vì hạn mức gói miễn phí rộng hơn các bản Flash; muốn câu trả lời tốt hơn thì dùng `gemini-3.8-flash` nhưng ít lượt miễn phí hơn. Hạn mức thật xem trong AI Studio. **Gói miễn phí có thể được Google dùng để cải thiện sản phẩm**: báo trước cho người dùng thử. Muốn đổi model chỉ cần sửa `GEMINI_MODEL`; lỗi tên model chỉ làm rơi xuống câu soạn sẵn.

### Đánh giá của người dùng thử (cho Người 5)

Dưới mỗi câu trả lời của bot (trừ lượt an toàn) có nút "Hữu ích"/"Chưa hợp". Mỗi lần bấm cũng ghi `rating` vào lượt tương ứng trong phiên (để hồ sơ nhạc dùng) và ghi thêm một dòng JSONL vào `FEEDBACK_PATH` gồm `session_id, turn_id, rating, emotion_label, arousal, goal, safety, llm_backend, created_at` — **không lưu nội dung tin nhắn hay câu trả lời**. Đổi đánh giá cho cùng lượt thì dòng mới thắng. Xuất CSV (mới nhất theo `turn_id`):

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/api/feedback/export -o feedback.csv
```

Cần đặt `ADMIN_TOKEN` trong `.env`; để trống thì route trả 404. File dữ liệu được `.gitignore` bỏ qua; trong Docker, mặc định file nằm ở `/app/data/runtime/feedback.jsonl` và production mount volume `emotion-data` vào thư mục này.

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
- Phiên: `session_id` và tin nhắn lưu trong localStorage (`ec.session_id`, `ec.messages.<id>`); nếu localStorage trống thì khôi phục từ `GET /api/session/{id}`. Danh sách cuộc trò chuyện ở sidebar lưu ở `ec.conversations` (tối đa 50 cuộc, chỉ trên trình duyệt đó).
- Bố cục: từ 1024px có sidebar cố định (thu gọn được, `Ctrl+B`); dưới 1024px (điện thoại, tablet) sidebar là ngăn kéo. Giao diện sáng/tối/theo hệ thống ở nút trên header.
- Bài hát: bấm thẻ mở popup trình phát YouTube (`SongPlayerDialog`: chuyển bài bằng nút hoặc phím ←/→, đóng là dừng phát). **Khi chạy ở `localhost`/`127.0.0.1`, nhiều video nhạc báo "This video is unavailable"** vì chủ video chỉ cho nhúng trên tên miền thật; trên https://emotion.hiennguyen.io.vn thì phát bình thường. Nút "Mở trên YouTube" luôn dùng được.
- Ghi âm: `useRecorder` (MediaRecorder, tự chọn `audio/webm;codecs=opus` > `audio/ogg;codecs=opus` > `audio/mp4`, tự dừng ở 30 giây), `useSpeechFallback` (Web Speech API `vi-VN`, chạy song song để hiện chữ trực tiếp và gửi `transcript_hint`), `RecordingBar`, `VoiceBubble`. Bản ghi để phát lại chỉ nằm trong RAM của tab (object URL, thu hồi khi bắt đầu cuộc trò chuyện mới) và không lưu vào localStorage.
- **Ghi âm cần `localhost` hoặc HTTPS** (secure context); mở bằng địa chỉ IP qua HTTP thì trình duyệt chặn micro và giao diện hiện thông báo, ô gõ chữ vẫn dùng bình thường.
- **Quyền riêng tư**: Web Speech API trên Chrome/Edge gửi âm thanh tới dịch vụ nhận dạng của hãng trình duyệt (Google/Microsoft). Nó chỉ là dự phòng hiển thị chữ trực tiếp; nguồn chính là PhoWhisper chạy ở backend của nhóm. Hãy nói rõ điều này với người dùng khi demo.

## Giới hạn

- UIT-VSMEC là bình luận mạng xã hội, lệch miền so với lời tâm sự.
- Không phân loại cảm xúc từ giọng nói; tông giọng chỉ là tín hiệu phụ (mức kích động).
- Không tuyên bố độ chính xác đa phương thức.
