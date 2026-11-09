"""POST /api/feedback và GET /api/feedback/export."""

import secrets

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response

from app import feedback
from app.config import get_settings
from app.schemas import FeedbackRequest, FeedbackResponse
from app.session import store

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(body: FeedbackRequest) -> FeedbackResponse:
    turns = await store.get_turns(body.session_id)
    turn = next((t for t in turns if t.turn_id == body.turn_id), None)
    if turn is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt trò chuyện này.")
    await feedback.save(
        {
            "session_id": body.session_id,
            "turn_id": body.turn_id,
            "rating": body.rating,
            "emotion_label": turn.emotion.label if turn.emotion else None,
            "arousal": turn.emotion.arousal if turn.emotion else None,
            "goal": turn.goal,
            "safety": turn.safety,
            "llm_backend": turn.llm_backend,
            "created_at": turn.created_at,
        }
    )
    return FeedbackResponse()


@router.get("/feedback/export")
async def export_feedback(authorization: str | None = Header(None)) -> Response:
    admin = get_settings().ADMIN_TOKEN
    if not admin:
        raise HTTPException(status_code=404, detail="Not Found")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(
        token.strip().encode(), admin.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Thiếu hoặc sai token quản trị.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Response(
        content=await feedback.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="feedback.csv"'},
    )
