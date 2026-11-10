# Hướng dẫn đóng góp

Mỗi thành viên chỉ sửa **đúng một file** trong `backend/modules/` (ổ cắm của mình). Phần ghép (`backend/app/`, `backend/mocks/`) là của Hiển; nếu cần đổi hãy nhắn trước.

| File | Hàm | Phụ trách |
|---|---|---|
| `modules/emotion.py` | `predict_emotion(text)` | Người 1 |
| `modules/speech.py` | `transcribe(wav_path)`, `extract_prosody(wav_path)` | Người 3 |
| `modules/safety.py` | `check_safety(text)` | Người 3 |
| `modules/llm.py` | `generate_reply(text, emotion, arousal, history, goal=None)` | Người 3 |
| `modules/music.py` | `recommend(label, arousal, goal, k=5)` | Người 5 |

Chữ ký, kiểu đầu vào/đầu ra nằm trong docstring của từng file. **Không đổi chữ ký**; nếu thấy cần đổi, báo Hiển để cập nhật cả mock và pipeline.

## Cắm module thật trong 3 bước

1. **Cài môi trường** (một lần), từ thư mục `backend/`:

   ```bash
   uv venv --python 3.11 .venv
   uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt   # Windows
   # Linux/macOS: uv pip install --python .venv/bin/python -r requirements-dev.txt
   uv pip install -r requirements-ml.txt   # chỉ khi cần chạy mô hình thật (torch, transformers, librosa)
   ```

2. **Viết ruột hàm** trong file `modules/<module>.py` của bạn (thay `raise NotImplementedError`). Chạy thử nhanh với mode `local`:

   ```bash
   MODEL_MODE=mock EMOTION_MODE=local python -m app.tools.try_module emotion "hôm nay vui ghê"
   ```

   (PowerShell: `$env:EMOTION_MODE="local"; python -m app.tools.try_module emotion "hôm nay vui ghê"`.)
   Các lệnh khác: `try_module safety "..."`, `try_module music Sadness --arousal low --goal xoa_diu`, `try_module speech <file.wav>`, `try_module llm "..." --goal xoa_diu`.

3. **Chạy contract test** của module. Test chạy trên cả bản mock và bản `local`; khi bạn implement xong, các test của bản `local` tự hết bị skip:

   ```bash
   pytest tests/contract -k emotion     # hoặc speech | safety | llm | music
   ```

   Module được coi là xong khi toàn bộ test của nó pass (không còn skip). Sau đó đặt `<MODULE>_MODE=local` trong `.env` để cả backend dùng bản thật.

## Quy tắc import lười (lazy import)

File trong `modules/` được import khi khởi động backend và trong notebook Colab. **Không import `torch`, `transformers`, `librosa`, `numpy`... ở đầu file.** Hãy import bên trong thân hàm, và tải mô hình một lần rồi cache:

```python
_model = None

def _get_model():
    global _model
    if _model is None:
        import torch                      # import nặng nằm trong hàm
        from transformers import AutoModelForSequenceClassification
        _model = AutoModelForSequenceClassification.from_pretrained("...")
    return _model
```

Test `test_import_is_light` sẽ báo lỗi nếu bạn import thư viện nặng ở đầu file.

## Quy tắc khác

- Hàm là **sync** (không `async`); backend chạy chúng trong threadpool với timeout. Hàm lỗi hoặc quá thời gian sẽ làm lượt chat chuyển sang dự phòng (`meta.degraded=true`), nên hãy tự bắt lỗi dễ đoán và trả kết quả hợp lệ.
- Không commit `.env`, khóa API, trọng số mô hình (`*.bin`, `*.safetensors`, `*.pt`), file audio.
- Chuỗi hiển thị cho người dùng viết bằng tiếng Việt có dấu; tên biến/hàm bằng tiếng Anh.
- `safety`: không tự bịa số điện thoại hỗ trợ. Số đường dây do Người 3 kiểm chứng rồi điền vào `SAFETY_HOTLINE_TEXT`.
- `music`: `backend/data/songs.csv` hiện có 33 bài demo với link YouTube thật (đã kiểm tra cho phép nhúng), nhãn `emotion_tags`/`goal_tags`/`energy` gắn tay để mô phỏng. Người 5 mở rộng và chuẩn hoá nhãn, giữ nguyên các cột; kiểm tra link mới bằng `https://www.youtube.com/oembed?format=json&url=<link>` (200 = tồn tại và cho nhúng).

## Nhánh và pull request

- Mỗi người làm trên nhánh `feat/<module>` (ví dụ `feat/emotion`, `feat/music`), tách từ `main`.
- Commit theo dạng conventional commits, ví dụ `feat(emotion): thêm CafeBERT predict_emotion`.
- Trước khi mở PR: `ruff check .` và `pytest -q` trong `backend/` đều phải pass.
- PR ghi rõ module nào đã qua `pytest tests/contract -k <module>`; Hiển review và merge vào `main`.
