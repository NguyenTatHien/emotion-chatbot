"""Tiện ích dùng chung cho contract test: chạy trên mock và local (skip nếu local còn là stub)."""

import importlib
import math
import struct
import wave

import pytest

VARIANTS = ["mock", "local"]
OWNERS = {
    "emotion": "Người 1",
    "speech": "Người 3",
    "safety": "Người 3",
    "llm": "Người 3",
    "music": "Người 5",
}


def load(variant: str, module: str):
    package = "mocks" if variant == "mock" else "modules"
    return importlib.import_module(f"{package}.{module}")


def call(variant: str, module: str, func: str, *args, **kwargs):
    """Gọi hàm của module; bản local còn là stub thì skip và nêu tên người phụ trách."""
    fn = getattr(load(variant, module), func)
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        if variant == "local":
            pytest.skip(f"Chưa implement — {OWNERS[module]} phụ trách ({module}.{func})")
        raise


@pytest.fixture
def sample_wav(tmp_path):
    """File WAV 16 kHz mono 1 giây (sóng sin 220 Hz) cho test speech."""
    path = tmp_path / "sample.wav"
    rate = 16000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate)))
            for i in range(rate)
        )
        w.writeframes(frames)
    return str(path)
