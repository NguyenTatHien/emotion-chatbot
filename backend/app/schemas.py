"""Schema Pydantic cho API."""

from typing import Literal

from pydantic import BaseModel, Field

Arousal = Literal["low", "medium", "high"]


class Emotion(BaseModel):
    label: str
    probs: dict[str, float]
    arousal: Arousal | None = None


class Song(BaseModel):
    title: str
    artist: str
    youtube_url: str
    reason: str = ""


class Meta(BaseModel):
    llm_backend: str
    model_mode: str
    modules: dict[str, str]
    degraded: bool = False
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    turn_id: str
    reply: str
    transcript: str | None = None
    emotion: Emotion | None = None
    songs: list[Song] = Field(default_factory=list)
    safety: bool = False
    meta: Meta


class SessionTurn(BaseModel):
    turn_id: str
    user_text: str
    transcript: str | None = None
    reply: str
    emotion: Emotion | None = None
    songs: list[Song] = Field(default_factory=list)
    safety: bool = False
    goal: str | None = None
    llm_backend: str | None = None
    created_at: str


class SessionResponse(BaseModel):
    session_id: str
    turns: list[SessionTurn]


class HealthResponse(BaseModel):
    ok: bool
    model_server: Literal["up", "down", "n/a"]


class MetaResponse(BaseModel):
    labels: list[str]
    goals: list[str]
    modules: dict[str, str]
    model_mode: str
    llm_backend: str


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    turn_id: str = Field(min_length=1, max_length=64)
    rating: Literal["up", "down"]


class FeedbackResponse(BaseModel):
    ok: bool = True
