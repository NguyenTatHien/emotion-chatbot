# Model server trên Colab

Server đích không có GPU nên CafeBERT, PhoWhisper và Qwen3-4B chạy trên **Colab T4** và được backend gọi qua tunnel ngrok. Thư mục này là **khung** để Người 3 chỉ việc chạy: `server_app.py` (FastAPI) gọi thẳng các hàm trong `backend/modules/*`, nên ruột mô hình chỉ viết một lần ở đó.

## Test nhanh trước khi các module xong

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/NguyenTatHien/emotion-chatbot/blob/main/colab/quick_test.ipynb)

`quick_test.ipynb` chạy toàn bộ trong một notebook: kiểm GPU, tải code, nạp mô hình, chạy thử từng module, bật `server_app.py` và mở ngrok, rồi in các Variable cần đặt trên GitHub. Module nào trong repo còn là khung (`NotImplementedError`) thì notebook dùng **bản tham khảo** trong `reference_modules/` (chỉ chép vào máy Colab, không sửa repo):

| Bản tham khảo | Mô hình | Ghi chú |
|---|---|---|
| `reference_modules/emotion.py` | `BaoNhan/cafebert-UITVSMEC` | `id2label` của checkpoint đúng thứ tự 7 nhãn |
| `reference_modules/speech.py` | `vinai/PhoWhisper-small` + librosa | ngưỡng kích động đặt tay, cần Người 3 hiệu chỉnh |
| `reference_modules/llm.py` | `Qwen/Qwen3-4B` fp16, `enable_thinking=False` | prompt giống bản Gemini |

Người 1 và Người 3 có thể dùng các file này làm điểm xuất phát; khi đã nộp code thật vào `backend/modules/`, notebook tự dùng code đó.

## Hợp đồng HTTP

| Route | Vào | Ra |
|---|---|---|
| `POST /emotion` | JSON `{text}` | kết quả `predict_emotion` (`{label, probs}`) |
| `POST /transcribe` | multipart `file` (WAV 16 kHz mono) | `{text}` |
| `POST /prosody` | multipart `file` | kết quả `extract_prosody` |
| `POST /generate` | JSON `{text, emotion, arousal, history, goal}` | `{reply}` |
| `GET /health` | | `{ok: true, modules: [...]}` (không cần token) |

Mọi route trừ `/health` yêu cầu header `X-Model-Server-Token` khớp biến môi trường `MODEL_SERVER_TOKEN` của server (nếu biến đó được đặt). Module còn là stub (`NotImplementedError`) trả HTTP 501; backend coi đó là lỗi và dùng dự phòng.

Safety và music **không** chạy ở đây: chúng luôn chạy trong backend để không phụ thuộc Colab.

## Chạy thử trên máy dev (không cần GPU)

```bash
pip install -r colab/requirements.txt
cd colab
SERVER_USE_MOCKS=1 MODEL_SERVER_TOKEN=thu-nghiem python -m uvicorn server_app:app --port 8001
```

`SERVER_USE_MOCKS=1` dùng `backend/mocks/*` thay cho `backend/modules/*`. Backend dùng thử:

```bash
cd backend
EMOTION_MODE=remote SPEECH_MODE=remote LLM_MODE=remote \
MODEL_SERVER_URL=http://127.0.0.1:8001 MODEL_SERVER_TOKEN=thu-nghiem \
python -m uvicorn app.main:app --workers 1
```

## Chạy trên Colab T4

Chọn Runtime → Change runtime type → **T4 GPU**. Trong notebook, mỗi khối dưới đây là một ô lệnh.

1. Lấy mã nguồn và cài phụ thuộc:

   ```python
   !git clone <URL-repo-emotion-chatbot> /content/emotion-chatbot
   %cd /content/emotion-chatbot
   !pip install -q -r colab/requirements.txt -r backend/requirements-ml.txt pyngrok
   ```

2. Đặt bí mật qua Colab Secrets (biểu tượng chìa khoá bên trái), không dán trực tiếp vào notebook:

   ```python
   import os
   from google.colab import userdata
   os.environ["MODEL_SERVER_TOKEN"] = userdata.get("MODEL_SERVER_TOKEN")
   os.environ["NGROK_AUTHTOKEN"] = userdata.get("NGROK_AUTHTOKEN")
   ```

3. Cấu hình mô hình trong `backend/modules/*` theo gợi ý:
   - Tải mô hình một lần rồi cache (xem quy tắc import lười trong `CONTRIBUTING.md`).
   - **fp16** trên T4: `torch_dtype=torch.float16`, `.to("cuda")`.
   - **Qwen3**: tắt chế độ suy luận bằng `enable_thinking=False` trong `tokenizer.apply_chat_template(...)`.

4. Chạy uvicorn ở nền:

   ```python
   import subprocess
   server = subprocess.Popen(
       ["python", "-m", "uvicorn", "server_app:app", "--host", "0.0.0.0", "--port", "8001"],
       cwd="/content/emotion-chatbot/colab",
   )
   ```

5. Mở tunnel bằng **ngrok** với dev domain cố định mà gói miễn phí cấp sẵn cho mỗi tài khoản (xem trong dashboard ngrok → Domains; gói free không tự đặt tên được, giới hạn 1 GB dữ liệu ra mỗi tháng, đủ cho JSON):

   ```python
   !ngrok config add-authtoken $NGROK_AUTHTOKEN
   !nohup ngrok http --url=<ten-mien-tinh>.ngrok-free.app 8001 > /content/ngrok.log 2>&1 &
   ```

6. Kiểm tra từ bất kỳ máy nào: `curl https://<ten-mien-tinh>.ngrok-free.app/health`.

> Vì URL ngrok là công khai, **luôn đặt `MODEL_SERVER_TOKEN`**. Dev domain không đổi giữa các lần chạy nên chỉ cần khai báo một lần; nếu dùng tunnel đổi URL (ví dụ Cloudflare quick tunnel) thì mỗi lần phải sửa `MODEL_SERVER_URL` rồi chạy lại Deploy.

## Cấu hình `.env` của backend tương ứng

Trên web thật không sửa `.env` bằng tay: đặt ở GitHub → Environments → production (Variable `MODEL_SERVER_URL`, `EMOTION_MODE`, `SPEECH_MODE`, `LLM_MODE`; Secret `MODEL_SERVER_TOKEN`) rồi chạy workflow Deploy, xem [deploy/README.md](../deploy/README.md#cấu-hình-module-từ-github-không-cần-ssh). Khi chạy backend trên máy mình thì dùng `.env` như dưới:

```env
EMOTION_MODE=remote
SPEECH_MODE=remote
LLM_MODE=remote
MODEL_SERVER_URL=https://<ten-mien-tinh>.ngrok-free.app
MODEL_SERVER_TOKEN=<cùng giá trị với secret trên Colab>
```

`SAFETY_MODE` và `MUSIC_MODE` giữ `mock` hoặc `local` (đặt `remote` sẽ bị báo lỗi khi khởi động). Khi Colab ngắt, backend vẫn trả HTTP 200 ở chế độ dự phòng: cảm xúc `Other`, câu trả lời từ Gemini (nếu có `GEMINI_API_KEY`) hoặc câu soạn sẵn.

Notebook chạy thật là của Người 3; thư mục này chỉ cung cấp server và hướng dẫn.
