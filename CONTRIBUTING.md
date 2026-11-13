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

   **Safety:** đã có bản `local` theo luật (regex, không mô hình, do Hiển viết thay, cần Người 3 review). Bật bằng `SAFETY_MODE=local`. Đo chất lượng trên bộ câu thử `backend/tests/data/safety_cases.csv` bằng `python -m app.tools.eval_safety` (thêm `--list-errors` để xem câu sai); bảng in recall, precision, số bỏ sót và báo nhầm theo nhóm. Khi thêm luật mới, thêm câu thử tương ứng vào CSV.

## Bật module của bạn trên web thật (https://emotion.hiennguyen.io.vn)

Cấu hình server đặt ở GitHub → Settings → Environments → **production** (cần quyền admin repo), không cần SSH. Bảng đầy đủ: [deploy/README.md](deploy/README.md#cấu-hình-module-từ-github-không-cần-ssh).

| Module | Chạy ở đâu | Bật thế nào |
|---|---|---|
| `safety`, `music` | Trong backend trên server | Merge code vào `main` (tự build + deploy), đặt Variable `SAFETY_MODE` / `MUSIC_MODE` = `local`, chạy Deploy |
| `emotion`, `speech`, `llm` | Colab T4 (server không có GPU) | Merge code vào `main`, chạy Colab theo [colab/README.md](colab/README.md), đặt Variable `MODEL_SERVER_URL` + Secret `MODEL_SERVER_TOKEN`, rồi `EMOTION_MODE` / `SPEECH_MODE` / `LLM_MODE` = `remote`, chạy Deploy |

Bật từng module một được (ví dụ chỉ `EMOTION_MODE=remote`, phần còn lại vẫn mock/Gemini). Đặt sai (thiếu URL, sai giá trị) thì Deploy báo đỏ và web giữ nguyên cấu hình cũ. Muốn tắt: đặt lại `mock` rồi chạy Deploy.

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
- `llm` (Người 3): backend yêu cầu **dòng đầu tiên** của câu trả lời là `[NHAC:CO]` hoặc `[NHAC:KHONG]` (xem system prompt trong `modules/llm.py` và `app/gemini.py`); backend tách thẻ trước khi trả về, không có thẻ thì không gợi ý nhạc (trừ khi người dùng bấm chip). Đừng tự cắt `history`: backend đã giới hạn độ dài và có thể đặt ở đầu một cặp tin bắt đầu bằng `[BỐI CẢNH CUỘC TRÒ CHUYỆN` (tóm tắt các lượt trước, không phải tin nhắn mới); nếu cần trần an toàn thì cắt theo số tin và luôn giữ cặp tin đó. Giữ nguyên chữ ký `generate_reply(text, emotion, arousal, history, goal=None)`.
- `music` (Người 5): `recommend()` không còn được gọi ở mọi lượt, chỉ khi người dùng bấm chip hoặc LLM gắn thẻ `[NHAC:CO]`; kết quả rỗng hoặc lỗi vẫn là trường hợp hợp lệ.
- `music`: `backend/data/songs.csv` hiện có 33 bài demo với link YouTube thật (đã kiểm tra cho phép nhúng), nhãn `emotion_tags`/`goal_tags`/`energy` gắn tay để mô phỏng. Người 5 mở rộng và chuẩn hoá nhãn, giữ nguyên các cột; kiểm tra link mới bằng `https://www.youtube.com/oembed?format=json&url=<link>` (200 = tồn tại và cho nhúng).

## Nhánh và pull request

- Mỗi người làm trên nhánh `feat/<module>` (ví dụ `feat/emotion`, `feat/music`), tách từ `main`.
- Commit theo dạng conventional commits, ví dụ `feat(emotion): thêm CafeBERT predict_emotion`.
- Trước khi mở PR: `ruff check .` và `pytest -q` trong `backend/` đều phải pass.
- PR ghi rõ module nào đã qua `pytest tests/contract -k <module>`; Hiển review và merge vào `main`.
