import io
import shutil
import sys
from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from app import audio


async def test_read_limited_stops_when_over_limit():
    upload = UploadFile(io.BytesIO(b"0" * (2 * 1024 * 1024 + 1)))
    with pytest.raises(audio.AudioTooLarge):
        await audio.read_limited(upload, 2)


async def test_read_limited_returns_bytes_within_limit():
    upload = UploadFile(io.BytesIO(b"abc" * 1000))
    assert await audio.read_limited(upload, 1) == b"abc" * 1000


def test_resolve_ffmpeg_accepts_explicit_path(set_env):
    exe = audio.resolve_ffmpeg()
    set_env(FFMPEG_BINARY=exe)
    assert audio.resolve_ffmpeg() == exe


def test_resolve_ffmpeg_missing(set_env, monkeypatch):
    set_env(FFMPEG_BINARY="khong-co-ffmpeg-nay")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
    with pytest.raises(audio.AudioToolMissing):
        audio.resolve_ffmpeg()


async def test_normalize_close_removes_dir(tmp_path, audio_samples):
    src = tmp_path / "in.webm"
    src.write_bytes(audio_samples["webm"])
    result = await audio.normalize(str(src))
    assert 4.5 < result.duration_s < 5.5
    assert Path(result.wav_path).exists()
    result.close()
    assert not Path(result.wav_path).exists()
    result.close()  # gọi lại vẫn an toàn


async def test_normalize_unreadable(tmp_path, audio_samples):
    src = tmp_path / "in.webm"
    src.write_bytes(audio_samples["text"])
    with pytest.raises(audio.AudioUnreadable):
        await audio.normalize(str(src))


async def test_normalize_too_long(tmp_path, audio_samples):
    src = tmp_path / "long.wav"
    src.write_bytes(audio_samples["long_wav"])
    with pytest.raises(audio.AudioTooLong):
        await audio.normalize(str(src))
