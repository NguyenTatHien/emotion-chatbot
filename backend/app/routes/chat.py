"""POST /api/chat."""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app import pipeline
from app.config import get_settings
from app.constants import GOALS, MAX_MESSAGE_CHARS
from app.schemas import ChatResponse

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
    suffix = ".wav"
    if audio_file is not None:
        limit = settings.MAX_AUDIO_MB * 1024 * 1024
        audio_bytes = await audio_file.read(limit + 1)
        if len(audio_bytes) > limit:
            raise _bad_request(f"File âm thanh quá lớn (tối đa {settings.MAX_AUDIO_MB} MB).")
        suffix = Path(audio_file.filename or "").suffix.lower() or ".wav"

    has_text = any(t and t.strip() for t in (message, transcript_hint))
    if not has_text and not audio_bytes:
        raise _bad_request(
            "Cần ít nhất một trong các trường: message, audio_file hoặc transcript_hint."
        )

    audio_path: str | None = None
    try:
        if audio_bytes:
            fd, audio_path = tempfile.mkstemp(suffix=suffix, prefix="chat_audio_")
            with os.fdopen(fd, "wb") as f:
                f.write(audio_bytes)
        return await pipeline.handle_chat(
            session_id=session_id,
            message=message,
            goal=goal,
            transcript_hint=transcript_hint,
            audio_path=audio_path,
        )
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
