"""Model server (khung) chạy trên Colab T4 hoặc máy dev.

Phục vụ các route trong hợp đồng HTTP bằng cách gọi thẳng `backend/modules/*`
(hoặc `backend/mocks/*` khi đặt `SERVER_USE_MOCKS=1`). File này KHÔNG chứa mã ML:
phần mô hình do Người 3 viết trong `backend/modules/`.

Chạy: uvicorn server_app:app --host 0.0.0.0 --port 8001   (từ thư mục colab/)

Biến môi trường:
  MODEL_SERVER_TOKEN  nếu đặt, mọi route trừ /health yêu cầu header X-Model-Server-Token khớp
  SERVER_USE_MOCKS    "1" để dùng mocks thay cho modules thật
"""

import importlib
import os
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SERVED_MODULES = ("emotion", "speech", "llm")
TOKEN_HEADER = "X-Model-Server-Token"


class EmotionIn(BaseModel):
    text: str


class GenerateIn(BaseModel):
    text: str
    emotion: dict
    arousal: str | None = None
    history: list[dict] = Field(default_factory=list)
    goal: str | None = None


def _use_mocks() -> bool:
    return os.environ.get("SERVER_USE_MOCKS", "").strip().lower() in {"1", "true", "yes"}


def _load_modules() -> dict:
    package = "mocks" if _use_mocks() else "modules"
    return {name: importlib.import_module(f"{package}.{name}") for name in SERVED_MODULES}


def require_token(
    x_model_server_token: str | None = Header(None, alias=TOKEN_HEADER),
) -> None:
    expected = os.environ.get("MODEL_SERVER_TOKEN", "")
    if not expected:
        return
    if not secrets.compare_digest((x_model_server_token or "").encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai token.")


async def _call(fn, *args):
    """Chạy hàm module (sync) trong threadpool; stub chưa viết -> 501."""
    try:
        return await run_in_threadpool(fn, *args)
    except NotImplementedError as exc:
        detail = str(exc) or "Module chưa được cài đặt."
        raise HTTPException(status_code=501, detail=detail) from None


async def _call_with_upload(fn, upload: UploadFile):
    tmpdir = tempfile.mkdtemp(prefix="model_server_")
    try:
        path = Path(tmpdir) / "audio.wav"
        with path.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        return await _call(fn, str(path))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def create_app() -> FastAPI:
    mods = _load_modules()
    app = FastAPI(title="Emotion Chatbot Model Server", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "modules": list(SERVED_MODULES), "mocks": _use_mocks()}

    @app.post("/emotion", dependencies=[Depends(require_token)])
    async def emotion(body: EmotionIn) -> dict:
        return await _call(mods["emotion"].predict_emotion, body.text)

    @app.post("/transcribe", dependencies=[Depends(require_token)])
    async def transcribe(file: UploadFile) -> dict:
        return {"text": await _call_with_upload(mods["speech"].transcribe, file)}

    @app.post("/prosody", dependencies=[Depends(require_token)])
    async def prosody(file: UploadFile) -> dict:
        return await _call_with_upload(mods["speech"].extract_prosody, file)

    @app.post("/generate", dependencies=[Depends(require_token)])
    async def generate(body: GenerateIn) -> dict:
        reply = await _call(
            mods["llm"].generate_reply,
            body.text,
            body.emotion,
            body.arousal,
            body.history,
            body.goal,
        )
        return {"reply": reply}

    return app


app = create_app()
