"""Ứng dụng FastAPI. Chạy: cd backend && uvicorn app.main:app --reload --workers 1"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.constants import MODULE_NAMES
from app.routes import chat, system

logger = logging.getLogger("emotion_chatbot")


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = get_settings()  # lỗi cấu hình (mode sai) sẽ dừng ứng dụng ngay tại đây

    app = FastAPI(title="Emotion Chatbot API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat.router, prefix="/api")
    app.include_router(system.router, prefix="/api")

    modes = {name: settings.module_mode(name) for name in MODULE_NAMES}
    logger.info("Chế độ module: %s", modes)
    return app


app = create_app()
