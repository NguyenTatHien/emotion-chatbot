"""GET /api/health, /api/meta, /api/session/{session_id}."""

from fastapi import APIRouter

from app import registry
from app.clients import model_server
from app.config import get_settings
from app.constants import GOALS, LABELS, MODULE_NAMES
from app.schemas import HealthResponse, MetaResponse, SessionResponse
from app.session import store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    uses_remote = any(registry.mode_of(n) == "remote" for n in MODULE_NAMES)
    if not uses_remote:
        return HealthResponse(ok=True, model_server="n/a")
    return HealthResponse(ok=True, model_server=await model_server.cached_health())


@router.get("/meta", response_model=MetaResponse)
async def meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        labels=LABELS,
        goals=GOALS,
        modules={n: registry.mode_of(n) for n in MODULE_NAMES},
        model_mode=settings.MODEL_MODE,
        llm_backend="mock" if registry.mode_of("llm") == "mock" else "qwen",
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def session(session_id: str) -> SessionResponse:
    return SessionResponse(session_id=session_id, turns=await store.get_turns(session_id))
