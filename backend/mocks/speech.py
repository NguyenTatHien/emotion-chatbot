"""Mock giọng nói: transcript cố định, arousal trung bình, không đọc file."""

from mocks._util import simulate_latency


def transcribe(wav_path: str) -> str:
    simulate_latency()
    return "hôm nay mình thấy hơi mệt"


def extract_prosody(wav_path: str) -> dict:
    simulate_latency()
    return {"arousal": "medium", "pitch_mean": 180.0, "energy_rms": 0.05, "speech_rate": 3.5}
