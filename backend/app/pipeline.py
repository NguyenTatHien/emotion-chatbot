"""Bộ điều phối một lượt chat: an toàn -> cảm xúc -> quyết định nhạc -> lưu phiên.

Late fusion (app/fusion.py) chạy ngay sau cảm xúc, trước LLM và nhạc.
Nhạc: safety -> không; có chip mục tiêu -> luôn có (llm || music song song);
còn lại do LLM quyết bằng thẻ `[NHAC:CO]` / `[NHAC:KHONG]` (music chạy sau llm).
"""

import asyncio
import inspect
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError

from app import fallbacks, gemini, memory, registry
from app.config import get_settings
from app.constants import AROUSAL_LEVELS, LABELS, MODULE_NAMES
from app.fusion import apply_fusion
from app.music_tag import split_music_tag
from app.schemas import ChatResponse, Emotion, Meta, MusicDecision, SessionTurn, Song
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
) -> tuple[str, str, list[str], bool | None]:
    """Sinh câu trả lời: implementation llm đang chọn -> Gemini (nếu có khoá) -> soạn sẵn.

    Với LLM_MODE=gemini, Gemini chính là implementation đang chọn nên không gọi lại lần hai.
    Thẻ nhạc được tách theo từng nguồn; nguồn chỉ còn chuỗi rỗng sau khi tách bị coi là rỗng.

    Trả (reply, nguồn thực tế, cảnh báo, music_flag). Nguồn: mock | qwen | gemini | canned.
    `music_flag`: True/False theo thẻ của nguồn đã dùng, None nếu không có thẻ (kể cả canned).
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
    if warn is None and isinstance(result, str):
        reply, flag = split_music_tag(result)
        if reply:
            return reply, registry.llm_backend_name(), warnings, flag
    warnings.append(warn or "llm: kết quả rỗng, dùng dự phòng")

    if settings.GEMINI_API_KEY.strip() and registry.mode_of("llm") != "gemini":
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
        if warn is None and isinstance(result, str):
            reply, flag = split_music_tag(result)
            if reply:
                return reply, "gemini", warnings, flag
        warnings.append(warn or "gemini: kết quả rỗng, dùng câu trả lời soạn sẵn")

    return fallbacks.canned_reply(emotion["label"]), "canned", warnings, None


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

    history = await memory.build_history(session_id)
    emotion_dict: dict | None = None
    fusion_applied = False
    songs: list[Song] = []
    music_decision: MusicDecision = "safety" if risk else "no_tag"

    llm_backend = "canned"
    if risk:
        reply = (safety_msg or "").strip() or fallbacks.safety_message()
    else:
        # Bước 3: cảm xúc.
        result, warn = await try_call(
            "emotion", registry.get("emotion"), text, timeout=settings.module_timeout("emotion")
        )
        emotion_dict = _valid_emotion(result) if warn is None else None
        from_module = emotion_dict is not None
        if emotion_dict is None:
            warnings.append(warn or "emotion: kết quả không hợp lệ, dùng dự phòng")
            emotion_dict = fallbacks.fallback_emotion()

        # Late fusion: giọng (arousal) điều chỉnh cảm xúc từ chữ trước khi dùng cho các bước sau.
        emotion_dict, fusion_applied = apply_fusion(
            emotion_dict, arousal, settings.FUSION_ALPHA, from_module
        )

        # Bước 4: quyết định nhạc. Có chip -> llm || music đồng thời; không chip -> llm trước,
        # chỉ gọi music khi LLM gắn thẻ CO.
        label = emotion_dict["label"]
        # LLM chỉ nhận contract {label, probs} (đã kết hợp nếu có fusion).
        llm_emotion = {"label": label, "probs": emotion_dict["probs"]}

        async def run_music() -> tuple[object | None, str | None]:
            return await try_call(
                "music",
                registry.get("music"),
                label,
                arousal,
                goal,
                5,
                timeout=settings.module_timeout("music"),
            )

        music_result: tuple[object | None, str | None] | None = None
        if goal:
            music_decision = "chip"
            reply_info, music_result = await asyncio.gather(
                generate_with_fallback(text, llm_emotion, arousal, history, goal), run_music()
            )
            reply, llm_backend, llm_warnings, _ = reply_info
        else:
            reply, llm_backend, llm_warnings, music_flag = await generate_with_fallback(
                text, llm_emotion, arousal, history, goal
            )
            if music_flag is True:
                music_decision = "llm"
                music_result = await run_music()
            else:
                music_decision = "llm_no" if music_flag is False else "no_tag"
        warnings.extend(llm_warnings)

        if music_result is not None:
            music_res, music_warn = music_result
            parsed = _valid_songs(music_res) if music_warn is None else None
            if parsed is None:
                warnings.append(music_warn or "music: kết quả không hợp lệ, trả danh sách rỗng")
            else:
                songs = parsed

    emotion = Emotion(**emotion_dict, arousal=arousal) if emotion_dict and not risk else None
    # Lượt an toàn không trả cảm xúc/nhạc.
    if risk:
        emotion, songs = None, []
        fusion_applied = False

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
            music_decision=music_decision,
            created_at=datetime.now(UTC).isoformat(),
        ),
    )

    await memory.maybe_schedule_summary(session_id)

    meta = Meta(
        llm_backend=llm_backend,
        model_mode=settings.MODEL_MODE,
        modules={name: registry.mode_of(name) for name in MODULE_NAMES},
        degraded=bool(warnings),
        latency_ms=int((time.perf_counter() - started) * 1000),
        warnings=warnings,
        music_decision=music_decision,
        fusion_applied=fusion_applied,
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
