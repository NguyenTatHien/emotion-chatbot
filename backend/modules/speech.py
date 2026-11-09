"""Hợp đồng module giọng nói — Người 3 phụ trách.

KHÔNG import librosa / torch / transformers ở đầu file; import bên trong thân hàm.
"""


def transcribe(wav_path: str) -> str:
    """Chuyển giọng nói thành văn bản (PhoWhisper).

    Đầu vào: đường dẫn file WAV 16 kHz mono.
    Đầu ra: chuỗi văn bản tiếng Việt (có thể rỗng nếu không nghe được).
    """
    raise NotImplementedError("Người 3 phụ trách: transcribe (PhoWhisper)")


def extract_prosody(wav_path: str) -> dict:
    """Trích đặc trưng tông giọng bằng librosa.

    Đầu ra: {"arousal": "low"|"medium"|"high", "pitch_mean": float,
             "energy_rms": float, "speech_rate": float}
    """
    raise NotImplementedError("Người 3 phụ trách: extract_prosody (librosa)")
