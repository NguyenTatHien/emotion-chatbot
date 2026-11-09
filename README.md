# Emotion Chatbot

Chatbot tiếng Việt nhận tin nhắn văn bản hoặc giọng nói, nhận diện cảm xúc người dùng, trả lời theo hướng đồng cảm và gợi ý 3–5 bài hát phù hợp. Đồ án cuối kỳ môn NLP501.

> Đây **không phải** công cụ chẩn đoán tâm lý. Khi phát hiện dấu hiệu tự làm hại, hệ thống chuyển sang thông điệp an toàn.

## Trạng thái

Đang khởi tạo repo. Khung backend, frontend và Docker sẽ được thêm theo kế hoạch 5 ngày.

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
| `llm.py` | `generate_reply(text, emotion, arousal, history)` | Người 3 |
| `music.py` | `recommend(label, arousal, goal, k)` | Người 5 |
| Backend, frontend, Docker | | Hiển (Người 4) |

## Giới hạn

- UIT-VSMEC là bình luận mạng xã hội, lệch miền so với lời tâm sự.
- Không phân loại cảm xúc từ giọng nói; tông giọng chỉ là tín hiệu phụ (mức kích động).
- Không tuyên bố độ chính xác đa phương thức.
