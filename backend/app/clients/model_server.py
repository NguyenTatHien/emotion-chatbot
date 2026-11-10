"""Client httpx async gọi model server (Colab) ở chế độ `remote`.

Hàm có chữ ký tương đương hợp đồng module để registry trả thẳng cho pipeline.
Mọi lỗi (HTTP, timeout, kết nối, sai schema) đều ném exception để `try_call` đưa vào dự phòng.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Literal, TypeVar

import httpx
from pydantic import BaseModel, ValidationError, field_validator

from app.config import get_settings
from app.constants import LABELS

logger = logging.getLogger("emotion_chatbot.model_server")

_M = TypeVar("_M", bound=BaseModel)

TOKEN_HEADER = "X-Model-Server-Token"
HEALTH_CACHE_SECONDS = 10.0

_client: httpx.AsyncClient | None = None
_health_cache: tuple[float, str] | None = None  # (thời điểm monotonic, "up" | "down")


class ModelServerError(Exception):
    """Model server trả lỗi hoặc phản hồi sai schema (thông điệp không chứa bí mật)."""


class _EmotionOut(BaseModel):
    label: str
    probs: dict[str, float]

    @field_validator("label")
    @classmethod
    def _label(cls, v: str) -> str:
        if v not in LABELS:
            raise ValueError("nhãn không hợp lệ")
        return v

    @field_validator("probs")
    @classmethod
    def _probs(cls, v: dict[str, float]) -> dict[str, float]:
        if any(k not in v for k in LABELS):
            raise ValueError("thiếu xác suất của nhãn")
        return {k: v[k] for k in LABELS}


class _TextOut(BaseModel):
    text: str


class _ProsodyOut(BaseModel):
    arousal: Literal["low", "medium", "high"]
    pitch_mean: float | None = None
    energy_rms: float | None = None
    speech_rate: float | None = None


class _ReplyOut(BaseModel):
    reply: str


def _headers() -> dict[str, str]:
    # ngrok gói free có thể chèn trang cảnh báo cho trình duyệt; header này bảo ngrok bỏ qua.
    headers = {"ngrok-skip-browser-warning": "1"}
    token = get_settings().MODEL_SERVER_TOKEN
    if token:
        headers[TOKEN_HEADER] = token
    return headers


def _base_url() -> str:
    return get_settings().MODEL_SERVER_URL.strip().rstrip("/")


async def startup() -> None:
    """Tạo AsyncClient dùng chung (gọi trong lifespan)."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient()


async def shutdown() -> None:
    global _client, _health_cache
    client, _client = _client, None
    _health_cache = None
    if client is not None:
        await client.aclose()


def reset_state() -> None:
    """Quên client và cache health (dùng trong test)."""
    global _client, _health_cache
    _client = None
    _health_cache = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:  # chưa qua lifespan (script, test): tạo khi cần
        _client = httpx.AsyncClient()
    return _client


async def _request(
    method: str, path: str, *, timeout: float, **kwargs
) -> object:
    url = f"{_base_url()}{path}"
    try:
        response = await _get_client().request(
            method, url, headers=_headers(), timeout=timeout, **kwargs
        )
    except httpx.TimeoutException:
        raise TimeoutError(f"model server {path} quá thời gian") from None
    except httpx.HTTPError as exc:
        raise ModelServerError(f"model server {path}: {type(exc).__name__}") from None
    if response.status_code != 200:
        raise ModelServerError(f"model server {path}: HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise ModelServerError(f"model server {path}: phản hồi không phải JSON") from None


def _parse(model: type[_M], data: object, path: str) -> _M:
    try:
        return model.model_validate(data)
    except ValidationError:
        raise ModelServerError(f"model server {path}: sai schema") from None


async def predict_emotion(text: str) -> dict:
    s = get_settings()
    data = await _request("POST", "/emotion", timeout=s.REMOTE_TIMEOUT_EMOTION, json={"text": text})
    out = _parse(_EmotionOut, data, "/emotion")
    return {"label": out.label, "probs": out.probs}


async def _upload(path: str, wav_path: str, timeout: float) -> object:
    content = await asyncio.to_thread(Path(wav_path).read_bytes)
    return await _request(
        "POST",
        path,
        timeout=timeout,
        files={"file": ("audio.wav", content, "audio/wav")},
    )


async def transcribe(wav_path: str) -> str:
    data = await _upload("/transcribe", wav_path, get_settings().REMOTE_TIMEOUT_TRANSCRIBE)
    return _parse(_TextOut, data, "/transcribe").text


async def extract_prosody(wav_path: str) -> dict:
    data = await _upload("/prosody", wav_path, get_settings().REMOTE_TIMEOUT_PROSODY)
    return _parse(_ProsodyOut, data, "/prosody").model_dump(exclude_none=True)


async def generate_reply(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None = None,
) -> str:
    payload = {
        "text": text,
        "emotion": emotion,
        "arousal": arousal,
        "history": history,
        "goal": goal,
    }
    data = await _request(
        "POST", "/generate", timeout=get_settings().REMOTE_TIMEOUT_GENERATE, json=payload
    )
    return _parse(_ReplyOut, data, "/generate").reply


async def health() -> bool:
    """True nếu `GET /health` của model server trả `{ok: true}`."""
    try:
        data = await _request("GET", "/health", timeout=get_settings().REMOTE_TIMEOUT_HEALTH)
    except Exception as exc:  # noqa: BLE001 - mọi lỗi đều nghĩa là "down"
        logger.info("Health model server lỗi: %r", exc)
        return False
    return isinstance(data, dict) and data.get("ok") is True


async def cached_health() -> Literal["up", "down"]:
    """Trạng thái model server, cache 10 giây để không dồn request lên Colab."""
    global _health_cache
    now = time.monotonic()
    if _health_cache is not None and now - _health_cache[0] < HEALTH_CACHE_SECONDS:
        return _health_cache[1]  # type: ignore[return-value]
    status = "up" if await health() else "down"
    _health_cache = (time.monotonic(), status)
    return status
