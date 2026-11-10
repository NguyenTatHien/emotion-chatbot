"""Module giọng nói — PhoWhisper (ASR) + librosa (prosody).

Thiết kế:
- Import librosa / torch / transformers BÊN TRONG hàm (lazy) — module phải
  nạp nhẹ (`tests/contract/test_import_is_light.py` kiểm chứng).
- `transcribe`: PhoWhisper của VinAI (`vinai/PhoWhisper-base`, fine-tune
  Whisper cho tiếng Việt). Backend đã chuẩn hoá audio thành WAV 16 kHz mono
  (`app/audio.py`), nên ở đây đọc trực tiếp, không xử lý lại.
- `extract_prosody`: librosa — RMS energy, pitch (pyin), speech rate ước
  lượng từ số peak năng lượng / giây. arousal chia 3 mức low/medium/high
  bằng ngưỡng heuristic (không có model SER — đúng phương án của Thầy).

Cache model ở mức module (`_ASR_STATE`) để không load lại mỗi request.
"""

_ASR_STATE: dict | None = None
_ASR_MODEL_NAME = "vinai/PhoWhisper-base"


def _get_asr():
    """Tải PhoWhisper pipeline 1 lần (lazy import)."""
    global _ASR_STATE
    if _ASR_STATE is not None:
        return _ASR_STATE

    import torch
    from transformers import pipeline

    pipe = pipeline(
        "automatic-speech-recognition",
        model=_ASR_MODEL_NAME,
        device=0 if torch.cuda.is_available() else -1,
    )
    _ASR_STATE = {"pipe": pipe}
    return _ASR_STATE


def transcribe(wav_path: str) -> str:
    """Chuyển giọng nói thành văn bản (PhoWhisper).

    Đầu vào: đường dẫn file WAV 16 kHz mono.
    Đầu ra: chuỗi văn bản tiếng Việt (có thể rỗng nếu không nghe được).
    """
    asr = _get_asr()

    # Whisper sinh text bằng decode vòng lặp: file không đọc được / quá rỗng
    # → trả chuỗi rỗng thay vì raise (contract cho phép rỗng).
    try:
        result = asr["pipe"](wav_path)
    except Exception:  # pylint:disable=broad-except - audio hỏng => rỗng
        return ""
    text = result.get("text", "") if isinstance(result, dict) else ""
    return (text or "").strip()


def extract_prosody(wav_path: str) -> dict:
    """Trích đặc trưng tông giọng bằng librosa.

    Đầu ra: {"arousal": "low"|"medium"|"high", "pitch_mean": float,
             "energy_rms": float, "speech_rate": float}
    """
    import librosa
    import numpy as np

    # Load 16 kHz mono — input chuẩn từ backend; resample lại phòng khi
    # sample_wav trong test hoặc file lạ khác sample rate.
    y, sr = librosa.load(wav_path, sr=16000, mono=True)
    duration = max(float(len(y)) / sr, 1e-6)

    # Energy RMS trung bình (0..~1 với amplitude chuẩn hoá).
    rms = librosa.feature.rms(y=y)[0]
    energy_rms = float(np.mean(rms)) if rms.size else 0.0

    # Pitch trung bình (pyin chậm trên file dài — giới hạn 30s như guard
    # của backend MAX_AUDIO_SECONDS=30).
    max_len = 30 * sr
    y_pitch = y[:max_len]
    f0 = librosa.pyin(
        y_pitch, fmin=70, fmax=400, sr=sr, frame_length=2048
    )[0]
    pitch_mean = float(np.nanmean(f0)) if f0 is not None and np.isfinite(f0).any() else 0.0

    # Speech rate: ước lượng số peak năng lượng rõ rệt (proxy cho số âm
    # tiết) trên giây. Dùng onsets (điểm biến thiên năng lượng) thay cho
    # word-level (cần ASR — tốn tài nguyên, nằm ngoài scope librosa).
    onset_strength = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(
        onset_envelope=onset_strength, sr=sr, units="time"
    )
    speech_rate = float(len(onsets) / duration)

    # Arousal heuristic: energy + độ dao động pitch. Ngưỡng hiệu chỉnh trên
    # amplitude chuẩn (librosa.load không chuẩn hoá, amplitude ∈ [-1, 1]).
    #  - low : energy < 0.02 (giọng nhỏ, xa mic, nền lặng)
    #  - high: energy > 0.08 HOẶC pitch_mean > 250 Hz (gần giọng trẻ em
    #          / nói to, cao giọng)
    #  - còn lại: medium
    if energy_rms > 0.08 or (pitch_mean > 250.0 and energy_rms > 0.04):
        arousal = "high"
    elif energy_rms < 0.02:
        arousal = "low"
    else:
        arousal = "medium"

    return {
        "arousal": arousal,
        "pitch_mean": pitch_mean,
        "energy_rms": energy_rms,
        "speech_rate": speech_rate,
    }
