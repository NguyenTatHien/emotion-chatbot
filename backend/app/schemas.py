"""Schema Pydantic cho API."""

from typing import Literal

from pydantic import BaseModel, Field

Arousal = Literal["low", "medium", "high"]
MusicDecision = Literal["chip", "llm", "llm_no", "no_tag", "safety"]
Rating = Literal["up", "down"]


class Emotion(BaseModel):
    label: str
    probs: dict[str, float]
    arousal: Arousal | None = None
    # Kết quả chỉ từ chữ; chỉ có giá trị khi late fusion được áp dụng.
    label_text: str | None = None
    probs_text: dict[str, float] | None = None


class Song(BaseModel):
    title: str
    artist: str
    youtube_url: str
    reason: str = ""


class Tone(BaseModel):
    key: str
    text: str


class RecentEmotion(BaseModel):
    turn: int
    # Nhãn cảm xúc của lượt; "safety" cho lượt có nội dung cần hỗ trợ an toàn.
    label: str


class Analysis(BaseModel):
    """Những gì pipeline đã dùng cho lượt này (khớp ghi chú bối cảnh gửi LLM)."""

    turn: int
    recent_emotions: list[RecentEmotion] = Field(default_factory=list)
    last_music_turn: int | None = None
    tone: Tone | None = None
    music_reason: str
    emotion_source: Literal["module", "fallback"] | None = None


class Meta(BaseModel):
    llm_backend: str
    model_mode: str
    modules: dict[str, str]
    degraded: bool = False
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    music_decision: MusicDecision = "no_tag"
    fusion_applied: bool = False
    analysis: Analysis | None = None


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
    music_decision: MusicDecision | None = None
    rating: Rating | None = None
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
    rating: Rating


class FeedbackResponse(BaseModel):
    ok: bool = True
