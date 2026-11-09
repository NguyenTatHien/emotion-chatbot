"""Cấu hình backend, đọc từ biến môi trường / file .env."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import MODES


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", protected_namespaces=()
    )

    MODEL_MODE: str = "mock"
    EMOTION_MODE: str | None = None
    SPEECH_MODE: str | None = None
    SAFETY_MODE: str | None = None
    LLM_MODE: str | None = None
    MUSIC_MODE: str | None = None

    MODEL_SERVER_URL: str = ""
    LLM_BACKEND: str = "mock"
    GEMINI_API_KEY: str = ""
    SONGS_CSV: str = "data/songs.csv"

    MAX_AUDIO_SECONDS: int = 30
    MAX_AUDIO_MB: int = 5
    HISTORY_TURNS: int = 6
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    SAFETY_TIMEOUT: float = 5.0
    EMOTION_TIMEOUT: float = 10.0
    LLM_TIMEOUT: float = 30.0
    MUSIC_TIMEOUT: float = 5.0
    SPEECH_TIMEOUT: float = 30.0

    SAFETY_HOTLINE_TEXT: str = ""
    MOCK_LATENCY_MS: int = 0

    @field_validator(
        "MODEL_MODE", "EMOTION_MODE", "SPEECH_MODE", "SAFETY_MODE", "LLM_MODE", "MUSIC_MODE",
        mode="before",
    )
    @classmethod
    def _normalize_mode(cls, value):
        if value is None:
            return None
        value = str(value).strip().lower()
        return value or None

    @field_validator(
        "MODEL_MODE", "EMOTION_MODE", "SPEECH_MODE", "SAFETY_MODE", "LLM_MODE", "MUSIC_MODE"
    )
    @classmethod
    def _check_mode(cls, value, info):
        if value is None:
            if info.field_name == "MODEL_MODE":
                return "mock"
            return None
        if value not in MODES:
            raise ValueError(
                f"{info.field_name}='{value}' không hợp lệ; chỉ chấp nhận: {', '.join(MODES)}"
            )
        return value

    def module_mode(self, name: str) -> str:
        """Mode của một module: biến riêng nếu có, không thì MODEL_MODE."""
        specific = getattr(self, f"{name.upper()}_MODE", None)
        return specific or self.MODEL_MODE

    def module_timeout(self, name: str) -> float:
        return float(getattr(self, f"{name.upper()}_TIMEOUT"))

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
