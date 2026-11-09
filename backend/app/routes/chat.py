"""POST /api/chat."""

import logging
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app import audio, pipeline
from app.config import get_settings
from app.constants import GOALS, MAX_MESSAGE_CHARS
from app.schemas import ChatResponse

logger = logging.getLogger("emotion_chatbot.chat")
router = APIRouter()


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    session_id: str | None = Form(None),
    message: str | None = Form(None),
    transcript_hint: str | None = Form(None),
    goal: str | None = Form(None),
    audio_file: UploadFile | None = None,
) -> ChatResponse:
    settings = get_settings()

    session_id = (session_id or "").strip()
    if not 1 <= len(session_id) <= 64:
        raise _bad_request("session_id là bắt buộc và dài từ 1 đến 64 ký tự.")
    if message is not None and len(message) > MAX_MESSAGE_CHARS:
        raise _bad_request(f"Tin nhắn quá dài (tối đa {MAX_MESSAGE_CHARS} ký tự).")
    if transcript_hint is not None and len(transcript_hint) > MAX_MESSAGE_CHARS:
        raise _bad_request(f"transcript_hint quá dài (tối đa {MAX_MESSAGE_CHARS} ký tự).")
    goal = (goal or "").strip() or None
    if goal is not None and goal not in GOALS:
        raise _bad_request(f"goal không hợp lệ; chỉ chấp nhận: {', '.join(GOALS)}.")

    audio_bytes = b""
    suffix = ".bin"
    if audio_file is not None:
        try:
            audio_bytes = await audio.read_limited(audio_file, settings.MAX_AUDIO_MB)
        except audio.AudioError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
        raw_suffix = Path(audio_file.filename or "").suffix.lower()
        if re.fullmatch(r"\.[a-z0-9]{1,5}", raw_suffix):
            suffix = raw_suffix

    has_text = any(t and t.strip() for t in (message, transcript_hint))
    if not has_text and not audio_bytes:
        raise _bad_request(
            "Cần ít nhất một trong các trường: message, audio_file hoặc transcript_hint."
        )

    raw_dir: tempfile.TemporaryDirectory | None = None
    normalized: audio.NormalizedAudio | None = None
    speech_warning: str | None = None
    try:
        if audio_bytes:
            raw_dir = tempfile.TemporaryDirectory(prefix="chat_audio_")
            raw_path = Path(raw_dir.name) / f"upload{suffix}"
            raw_path.write_bytes(audio_bytes)
            try:
                normalized = await audio.normalize(str(raw_path))
            except audio.AudioToolMissing as exc:
                logger.warning("Không có ffmpeg, bỏ qua bước speech: %s", exc.message)
                speech_warning = "speech: chưa có ffmpeg trên máy chủ, dùng dự phòng"
            except audio.AudioError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
        try:
            return await pipeline.handle_chat(
                session_id=session_id,
                message=message,
                goal=goal,
                transcript_hint=transcript_hint,
                audio_path=normalized.wav_path if normalized else None,
                speech_warning=speech_warning,
            )
        except pipeline.NoUsableInput as exc:
            raise _bad_request(str(exc)) from None
    finally:
        if normalized:
            normalized.close()
        if raw_dir:
            raw_dir.cleanup()
