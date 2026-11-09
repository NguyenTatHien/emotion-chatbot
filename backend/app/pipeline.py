"""Bộ điều phối một lượt chat: an toàn -> cảm xúc -> (llm || nhạc) -> lưu phiên."""

import asyncio
import inspect
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError

from app import fallbacks, gemini, registry
from app.config import get_settings
from app.constants import AROUSAL_LEVELS, LABELS, MODULE_NAMES
from app.schemas import ChatResponse, Emotion, Meta, SessionTurn, Song
from app.session import store

logger = logging.getLogger("emotion_chatbot.pipeline")


class NoUsableInput(Exception):
    """Không có chữ nào để xử lý (audio không nhận dạng được, không có message/hint)."""


async def try_call(
    name: str, fn: Callable, *args, timeout: float, **kwargs
) -> tuple[object | None, str | None]:
    """Chạy hàm với timeout: hàm async được await trực tiếp, hàm sync chạy trong threadpool.

    Trả (kết quả, None) nếu thành công hoặc (None, cảnh báo) nếu lỗi/quá thời gian.
    Thread bị timeout vẫn chạy nốt ở nền (không thể giết thread) — chấp nhận cho demo.
    """
    try:
        if inspect.iscoroutinefunction(fn):
            result = await asyncio.wait_for(fn(*args, **kwargs), timeout)
        else:
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


async def generate_with_fallback(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None,
) -> tuple[str, str, list[str]]:
    """Sinh câu trả lời: implementation llm đang chọn -> Gemini (nếu có khoá) -> soạn sẵn.

    Trả (reply, nguồn thực tế, cảnh báo). Nguồn: mock | qwen | gemini | canned.
    """
    settings = get_settings()
    warnings: list[str] = []

    result, warn = await try_call(
        "llm",
        registry.get("llm"),
        text,
        emotion,
        arousal,
        history,
        goal,
        timeout=settings.module_timeout("llm"),
    )
    if warn is None and isinstance(result, str) and result.strip():
        backend = "mock" if registry.mode_of("llm") == "mock" else "qwen"
        return result.strip(), backend, warnings
    warnings.append(warn or "llm: kết quả rỗng, dùng dự phòng")

    if settings.GEMINI_API_KEY.strip():
        result, warn = await try_call(
            "gemini",
            gemini.generate_reply,
            text,
            emotion,
            arousal,
            history,
            goal,
            timeout=settings.GEMINI_TIMEOUT,
        )
        if warn is None and isinstance(result, str) and result.strip():
            return result.strip(), "gemini", warnings
        warnings.append(warn or "gemini: kết quả rỗng, dùng câu trả lời soạn sẵn")

    return fallbacks.canned_reply(emotion["label"]), "canned", warnings


async def handle_chat(
    session_id: str,
    message: str | None = None,
    goal: str | None = None,
    transcript_hint: str | None = None,
    audio_path: str | None = None,
    transcript: str | None = None,
    speech_warning: str | None = None,
) -> ChatResponse:
    settings = get_settings()
    started = time.perf_counter()
    warnings: list[str] = []
    arousal: str | None = None
    w1: str | None = None

    # Bước 0: nếu có audio thì chạy speech (transcribe || prosody) qua registry.
    heard: str | None = None
    if audio_path:
        (heard_raw, w1), (prosody, w2) = await asyncio.gather(
            try_call(
                "speech.transcribe",
                registry.get("speech", "transcribe"),
                audio_path,
                timeout=settings.module_timeout("speech"),
            ),
            try_call(
                "speech.prosody",
                registry.get("speech", "extract_prosody"),
                audio_path,
                timeout=settings.PROSODY_TIMEOUT,
            ),
        )
        warnings.extend(w for w in (w1, w2) if w)
        if isinstance(heard_raw, str) and heard_raw.strip():
            heard = heard_raw.strip()
        if isinstance(prosody, dict) and prosody.get("arousal") in AROUSAL_LEVELS:
            arousal = prosody["arousal"]
    if speech_warning:
        warnings.append(speech_warning)

    hint = (transcript_hint or "").strip() or None
    if heard:
        transcript = heard
    elif (audio_path or speech_warning) and hint:
        # Có audio nhưng PhoWhisper lỗi/rỗng: dùng chữ nhận dạng sẵn từ trình duyệt.
        transcript = hint
        if not w1 and not speech_warning:
            warnings.append("speech: không nhận dạng được, dùng transcript_hint")

    # Bước 1: văn bản đầu vào theo ưu tiên message > transcript > transcript_hint.
    text = next(
        (t.strip() for t in (message, transcript, transcript_hint) if t and t.strip()), ""
    )
    if not text:
        raise NoUsableInput(
            "Mình chưa nghe rõ bạn nói gì. Bạn thử ghi âm lại hoặc gõ chữ giúp mình nhé."
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

    llm_backend = "canned"
    if risk:
        reply = (safety_msg or "").strip() or fallbacks.safety_message()
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
        (reply_info, (music_res, music_warn)) = await asyncio.gather(
            generate_with_fallback(text, emotion_dict, arousal, history, goal),
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
        reply, llm_backend, llm_warnings = reply_info
        warnings.extend(llm_warnings)

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
            goal=goal,
            llm_backend=llm_backend,
            created_at=datetime.now(UTC).isoformat(),
        ),
    )

    meta = Meta(
        llm_backend=llm_backend,
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
