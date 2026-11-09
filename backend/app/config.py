"""Cấu hình backend, đọc từ biến môi trường / file .env."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import MODES, MODULE_NAMES


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
    MODEL_SERVER_TOKEN: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    ADMIN_TOKEN: str = ""
    FEEDBACK_PATH: str = "data/runtime/feedback.jsonl"
    SONGS_CSV: str = "data/songs.csv"

    MAX_AUDIO_SECONDS: int = 30
    MAX_AUDIO_MB: int = 5
    FFMPEG_BINARY: str = "ffmpeg"
    HISTORY_TURNS: int = 6
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    SAFETY_TIMEOUT: float = 5.0
    EMOTION_TIMEOUT: float = 10.0
    LLM_TIMEOUT: float = 30.0
    MUSIC_TIMEOUT: float = 5.0
    SPEECH_TIMEOUT: float = 20.0  # transcribe
    PROSODY_TIMEOUT: float = 10.0
    GEMINI_TIMEOUT: float = 20.0

    # Timeout của từng lời gọi HTTP tới model server (giây).
    REMOTE_TIMEOUT_EMOTION: float = 10.0
    REMOTE_TIMEOUT_TRANSCRIBE: float = 20.0
    REMOTE_TIMEOUT_PROSODY: float = 10.0
    REMOTE_TIMEOUT_GENERATE: float = 30.0
    REMOTE_TIMEOUT_HEALTH: float = 3.0

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

    def validate_remote(self) -> None:
        """Báo lỗi cấu hình rõ ràng khi khởi động nếu mode `remote` dùng sai."""
        for name in ("safety", "music"):
            if self.module_mode(name) == "remote":
                raise ValueError(
                    f"{name.upper()}_MODE=remote không được hỗ trợ: module '{name}' "
                    "luôn chạy trong backend (mock hoặc local)."
                )
        remote = [n for n in MODULE_NAMES if self.module_mode(n) == "remote"]
        if remote and not self.MODEL_SERVER_URL.strip():
            raise ValueError(
                f"Module {', '.join(remote)} ở mode remote nhưng MODEL_SERVER_URL đang trống."
            )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
