"""BẢN THAM KHẢO để test nhanh trên Colab — không phải bản nộp của Người 3.

Notebook `colab/quick_test.ipynb` chép file này vào `backend/modules/speech.py` của máy Colab.
- transcribe(): PhoWhisper (mặc định vinai/PhoWhisper-small; đổi bằng ASR_MODEL_ID, ví dụ -medium).
- extract_prosody(): librosa đo độ to (RMS), cao độ (YIN), tốc độ nói (số onset/giây), rồi quy
  ra mức kích động bằng NGƯỠNG ĐẶT TAY. Ngưỡng này chỉ để chạy thử; Người 3 cần chỉnh lại bằng
  vài bản ghi thật (đọc 3 kiểu: nhỏ nhẹ, bình thường, kích động).

Audio đầu vào đã được backend chuẩn hoá thành WAV 16 kHz mono.
Thư viện nặng chỉ import trong thân hàm (contract test kiểm tra điều này).
"""

import os

ASR_MODEL_ID = os.environ.get("ASR_MODEL_ID", "vinai/PhoWhisper-small")
SAMPLE_RATE = 16000

# Ngưỡng tạm (cần hiệu chỉnh): RMS trung bình và số onset mỗi giây.
HIGH_ENERGY = 0.08
LOW_ENERGY = 0.025
HIGH_RATE = 5.0
LOW_RATE = 3.0

_state: dict = {}


def _load_audio(wav_path: str):
    import librosa

    audio, _ = librosa.load(wav_path, sr=SAMPLE_RATE, mono=True)
    return audio


def _asr():
    if "asr" not in _state:
        import torch
        from transformers import pipeline

        cuda = torch.cuda.is_available()
        _state["asr"] = pipeline(
            "automatic-speech-recognition",
            model=ASR_MODEL_ID,
            device=0 if cuda else -1,
            dtype=torch.float16 if cuda else torch.float32,
        )
    return _state["asr"]


def transcribe(wav_path: str) -> str:
    """WAV 16 kHz mono (tối đa 30 giây) -> văn bản tiếng Việt."""
    audio = _load_audio(wav_path)
    if audio.size == 0:
        return ""
    result = _asr()({"raw": audio, "sampling_rate": SAMPLE_RATE})
    return str(result.get("text", "")).strip()


def extract_prosody(wav_path: str) -> dict:
    """-> {"arousal": "low"|"medium"|"high", "pitch_mean", "energy_rms", "speech_rate"}."""
    import librosa
    import numpy as np

    audio = _load_audio(wav_path)
    duration = audio.size / SAMPLE_RATE
    if duration < 0.2:
        return {"arousal": "low", "pitch_mean": 0.0, "energy_rms": 0.0, "speech_rate": 0.0}

    energy = float(np.mean(librosa.feature.rms(y=audio)[0]))
    f0 = librosa.yin(audio, fmin=65, fmax=400, sr=SAMPLE_RATE)
    pitch = float(np.median(f0[np.isfinite(f0)])) if np.isfinite(f0).any() else 0.0
    onsets = librosa.onset.onset_detect(y=audio, sr=SAMPLE_RATE, units="time")
    rate = float(len(onsets) / duration)

    if energy >= HIGH_ENERGY or (rate >= HIGH_RATE and energy >= LOW_ENERGY):
        arousal = "high"
    elif energy < LOW_ENERGY and rate < LOW_RATE:
        arousal = "low"
    else:
        arousal = "medium"
    return {
        "arousal": arousal,
        "pitch_mean": round(pitch, 1),
        "energy_rms": round(energy, 4),
        "speech_rate": round(rate, 2),
    }
