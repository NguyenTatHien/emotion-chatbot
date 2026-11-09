"""Bộ điều phối một lượt chat: an toàn -> cảm xúc -> (llm || nhạc) -> lưu phiên."""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError

from app import fallbacks, registry
from app.config import get_settings
from app.constants import AROUSAL_LEVELS, LABELS, MODULE_NAMES
from app.schemas import ChatResponse, Emotion, Meta, SessionTurn, Song
from app.session import store

logger = logging.getLogger("emotion_chatbot.pipeline")


async def try_call(
    name: str, fn: Callable, *args, timeout: float, **kwargs
) -> tuple[object | None, str | None]:
    """Chạy hàm sync trong threadpool với timeout.

    Trả (kết quả, None) nếu thành công hoặc (None, cảnh báo) nếu lỗi/quá thời gian.
    Thread bị timeout vẫn chạy nốt ở nền (không thể giết thread) — chấp nhận cho demo.
    """
    try:
        result = await asyncio.wait_for(asyncio.to_thread(fn, *args, **kwargs), timeout)
        return result, None
    except TimeoutError:
        logger.warning("Module %s quá thời gian (%.1fs)", name, timeout)
        return None, f"{name}: quá thời gian ({timeout:g}s), dùng dự phòng"
    except Exception as exc:  # noqa: BLE001 - mọi lỗi module đều phải rơi vào dự phòng
        logger.warning("Module %s lỗi: %r", name, exc)
        return None, f"{name}: lỗi {type(exc).__name__}, dùng dự phòng"


def _valid_emotion(result: object) -> dict | None:
    if not isinstance(result, dict):
        return None
    label, probs = result.get("label"), result.get("probs")
    if label not in LABELS or not isinstance(probs, dict):
        return None
    if any(k not in probs for k in LABELS):
        return None
    try:
        return {"label": label, "probs": {k: float(probs[k]) for k in LABELS}}
    except (TypeError, ValueError):
        return None


def _valid_songs(result: object) -> list[Song] | None:
    if not isinstance(result, list):
        return None
    try:
        return [Song(**item) for item in result]
    except (ValidationError, TypeError):
        return None


async def handle_chat(
    session_id: str,
    message: str | None = None,
    goal: str | None = None,
    transcript_hint: str | None = None,
    audio_path: str | None = None,
    transcript: str | None = None,
) -> ChatResponse:
    settings = get_settings()
    started = time.perf_counter()
    warnings: list[str] = []
    arousal: str | None = None

    # Bước 0: nếu có audio thì chạy speech (transcribe || prosody) qua registry.
    if audio_path:
        timeout = settings.module_timeout("speech")
        (heard, w1), (prosody, w2) = await asyncio.gather(
            try_call("speech", registry.get("speech", "transcribe"), audio_path, timeout=timeout),
            try_call(
                "speech", registry.get("speech", "extract_prosody"), audio_path, timeout=timeout
            ),
        )
        warnings.extend(w for w in (w1, w2) if w)
        if isinstance(heard, str) and heard.strip():
            transcript = heard.strip()
        if isinstance(prosody, dict) and prosody.get("arousal") in AROUSAL_LEVELS:
            arousal = prosody["arousal"]

    # Bước 1: văn bản đầu vào theo ưu tiên message > transcript > transcript_hint.
    text = next(
        (t.strip() for t in (message, transcript, transcript_hint) if t and t.strip()), ""
    )

    # Bước 2: an toàn chạy trước, fail-closed.
    risk = False
    safety_msg: str | None = None
    result, warn = await try_call(
        "safety", registry.get("safety"), text, timeout=settings.module_timeout("safety")
    )
    if warn is None and isinstance(result, dict) and "risk" in result:
        risk = bool(result["risk"])
        safety_msg = result.get("message")
    else:
        if warn is None:
            warn = "safety: kết quả không hợp lệ, dùng bộ kiểm từ khóa dự phòng"
        warnings.append(warn)
        risk = fallbacks.keyword_safety(text)

    history = await store.history_for_llm(session_id, settings.HISTORY_TURNS)
    emotion_dict: dict | None = None
    songs: list[Song] = []

    if risk:
        reply = (safety_msg or "").strip() or fallbacks.safety_message()
    elif not text:
        # Có audio nhưng không nghe được gì: không đoán cảm xúc.
        emotion_dict = fallbacks.fallback_emotion()
        reply = "Mình chưa nghe rõ bạn nói gì. Bạn có thể nói lại hoặc gõ chữ giúp mình không?"
        warnings.append("speech: không có nội dung để xử lý")
    else:
        # Bước 3: cảm xúc.
        result, warn = await try_call(
            "emotion", registry.get("emotion"), text, timeout=settings.module_timeout("emotion")
        )
        emotion_dict = _valid_emotion(result) if warn is None else None
        if emotion_dict is None:
            warnings.append(warn or "emotion: kết quả không hợp lệ, dùng dự phòng")
            emotion_dict = fallbacks.fallback_emotion()

        # Bước 4: llm || music chạy đồng thời.
        label = emotion_dict["label"]
        (llm_res, llm_warn), (music_res, music_warn) = await asyncio.gather(
            try_call(
                "llm",
                registry.get("llm"),
                text,
                emotion_dict,
                arousal,
                history,
                goal,
                timeout=settings.module_timeout("llm"),
            ),
            try_call(
                "music",
                registry.get("music"),
                label,
                arousal,
                goal,
                5,
                timeout=settings.module_timeout("music"),
            ),
        )
        if llm_warn is None and isinstance(llm_res, str) and llm_res.strip():
            reply = llm_res.strip()
        else:
            warnings.append(llm_warn or "llm: kết quả rỗng, dùng câu trả lời soạn sẵn")
            reply = fallbacks.canned_reply(label)

        parsed = _valid_songs(music_res) if music_warn is None else None
        if parsed is None:
            warnings.append(music_warn or "music: kết quả không hợp lệ, trả danh sách rỗng")
        else:
            songs = parsed

    emotion = Emotion(**emotion_dict, arousal=arousal) if emotion_dict and not risk else None
    # Lượt an toàn không trả cảm xúc/nhạc.
    if risk:
        emotion, songs = None, []

    turn_id = str(uuid.uuid4())
    await store.append_turn(
        session_id,
        SessionTurn(
            turn_id=turn_id,
            user_text=text,
            transcript=transcript,
            reply=reply,
            emotion=emotion,
            songs=songs,
            safety=risk,
            created_at=datetime.now(UTC).isoformat(),
        ),
    )

    meta = Meta(
        llm_backend=settings.LLM_BACKEND,
        model_mode=settings.MODEL_MODE,
        modules={name: registry.mode_of(name) for name in MODULE_NAMES},
        degraded=bool(warnings),
        latency_ms=int((time.perf_counter() - started) * 1000),
        warnings=warnings,
    )
    return ChatResponse(
        turn_id=turn_id,
        reply=reply,
        transcript=transcript,
        emotion=emotion,
        songs=songs,
        safety=risk,
        meta=meta,
    )
