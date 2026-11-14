"""Chuẩn hoá audio người dùng gửi lên thành WAV PCM 16-bit, 16 kHz, mono bằng ffmpeg.

Module speech (PhoWhisper, librosa) chỉ nhận WAV 16 kHz mono, trong khi trình duyệt gửi
webm/opus (Chrome, Edge, Firefox), ogg hoặc mp4/aac (Safari).
"""

import asyncio
import logging
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("emotion_chatbot.audio")

FFMPEG_TIMEOUT_S = 15
CHUNK_BYTES = 64 * 1024
# Đọc dư một chút so với giới hạn để phát hiện bản ghi quá dài mà không giải mã cả file.
READ_MARGIN_S = 1.5
# Dung sai khi so thời lượng đo được với giới hạn.
DURATION_TOLERANCE_S = 1.0

# Bản WAV riêng cho đo mức kích động: bỏ mọi đoạn lặng (đầu, cuối và giữa câu dài hơn 0,3 s)
# để độ to trung bình phản ánh lúc đang nói, không bị khoảng lặng kéo xuống.
SILENCE_THRESHOLD = "-45dB"
SILENCE_FILTER = (
    f"silenceremove=start_periods=1:start_threshold={SILENCE_THRESHOLD}:"
    f"stop_periods=-1:stop_duration=0.3:stop_threshold={SILENCE_THRESHOLD}"
)
# Bản cắt ngắn hơn mức này (ví dụ thì thầm rất nhỏ bị coi là lặng) thì dùng lại bản đầy đủ.
MIN_TRIMMED_S = 0.3


class AudioError(Exception):
    """Lỗi xử lý audio; `message` là thông điệp tiếng Việt hiển thị cho người dùng."""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AudioTooLarge(AudioError):
    status_code = 413


class AudioTooLong(AudioError):
    status_code = 413


class AudioUnreadable(AudioError):
    status_code = 415


class AudioToolMissing(AudioError):
    """Không tìm thấy ffmpeg: không phải lỗi của người dùng, pipeline sẽ dùng dự phòng."""

    status_code = 503


@dataclass
class NormalizedAudio:
    wav_path: str
    duration_s: float
    # WAV đã bỏ khoảng lặng, chỉ dùng để đo mức kích động; None = dùng `wav_path`.
    prosody_path: str | None = None
    _tmpdir: tempfile.TemporaryDirectory | None = field(default=None, repr=False)

    def close(self) -> None:
        """Xoá thư mục tạm chứa file WAV (gọi nhiều lần cũng an toàn)."""
        if self._tmpdir is not None:
            self._tmpdir.cleanup()
            self._tmpdir = None


def resolve_ffmpeg() -> str:
    """Tìm ffmpeg: `FFMPEG_BINARY` (mặc định `ffmpeg`) trên PATH, rồi imageio-ffmpeg."""
    binary = get_settings().FFMPEG_BINARY.strip() or "ffmpeg"
    found = shutil.which(binary)
    if found:
        return found
    try:
        import imageio_ffmpeg  # chỉ có trong requirements-dev.txt

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - thiếu gói hoặc thiếu binary đều coi là không có ffmpeg
        raise AudioToolMissing(
            "Máy chủ chưa cài ffmpeg nên chưa xử lý được âm thanh."
        ) from None


async def read_limited(upload, max_mb: int) -> bytes:
    """Đọc UploadFile theo khối, dừng ngay khi vượt `max_mb` MB (chưa ghi gì ra đĩa)."""
    limit = max_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise AudioTooLarge(f"File âm thanh quá lớn (tối đa {max_mb} MB).")
        chunks.append(chunk)
    return b"".join(chunks)


def _wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            rate = w.getframerate()
            return w.getnframes() / rate if rate else 0.0
    except (wave.Error, EOFError, OSError):
        return 0.0


def _run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - danh sách tham số, không qua shell
        args, capture_output=True, timeout=FFMPEG_TIMEOUT_S, check=False
    )


async def normalize(path: str) -> NormalizedAudio:
    """Chuyển file audio bất kỳ sang WAV 16 kHz mono; ném AudioTooLong/AudioUnreadable/..."""
    settings = get_settings()
    max_s = settings.MAX_AUDIO_SECONDS
    ffmpeg = resolve_ffmpeg()

    tmpdir = tempfile.TemporaryDirectory(prefix="chat_wav_")
    out = Path(tmpdir.name) / "normalized.wav"
    args = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(path),
        "-t", f"{max_s + READ_MARGIN_S:g}",
        "-vn", "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        str(out),
    ]  # fmt: skip
    try:
        try:
            proc = await asyncio.to_thread(_run_ffmpeg, args)
        except FileNotFoundError:
            raise AudioToolMissing(
                "Máy chủ chưa cài ffmpeg nên chưa xử lý được âm thanh."
            ) from None
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg quá thời gian %ss", FFMPEG_TIMEOUT_S)
            raise AudioUnreadable("Không đọc được file âm thanh (xử lý quá lâu).") from None

        if proc.returncode != 0 or not out.exists():
            logger.info("ffmpeg không giải mã được: %s", proc.stderr.decode(errors="replace")[:300])
            raise AudioUnreadable("Không đọc được file âm thanh. Hãy thử ghi âm lại hoặc gõ chữ.")

        duration = _wav_duration(out)
        if duration <= 0:
            raise AudioUnreadable("File âm thanh rỗng hoặc không có nội dung.")
        if duration >= max_s + DURATION_TOLERANCE_S:
            raise AudioTooLong(f"Bản ghi quá dài (tối đa {max_s} giây).")
    except BaseException:
        tmpdir.cleanup()
        raise
    prosody = await _trim_silence(ffmpeg, out, Path(tmpdir.name) / "prosody.wav")
    return NormalizedAudio(
        wav_path=str(out), duration_s=duration, prosody_path=prosody, _tmpdir=tmpdir
    )


async def _trim_silence(ffmpeg: str, src: Path, dst: Path) -> str | None:
    """Tạo bản WAV bỏ khoảng lặng cho bước đo mức kích động.

    Lỗi, quá thời gian, hoặc bản cắt quá ngắn thì trả None (pipeline dùng bản đầy đủ):
    bước này chỉ để đo chính xác hơn, không bao giờ làm hỏng lượt chat.
    """
    args = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src), "-af", SILENCE_FILTER,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        str(dst),
    ]  # fmt: skip
    try:
        proc = await asyncio.to_thread(_run_ffmpeg, args)
        if proc.returncode != 0 or not dst.exists():
            return None
        if _wav_duration(dst) < MIN_TRIMMED_S:
            return None
    except Exception as exc:  # noqa: BLE001 - cắt lặng là tuỳ chọn
        logger.info("Không cắt được khoảng lặng, dùng bản đầy đủ: %r", exc)
        return None
    return str(dst)
