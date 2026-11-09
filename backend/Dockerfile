# syntax=docker/dockerfile:1
# Target `base`: nhẹ, chạy được mock/remote (không có torch).
# Target `ml`: thêm torch CPU + transformers + librosa để chạy mode `local`.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app/ app/
COPY modules/ modules/
COPY mocks/ mocks/
COPY data/songs.csv data/songs.csv

# Thư mục dữ liệu ghi được (feedback.jsonl); mount volume vào đây khi chạy production.
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /app/data/runtime \
    && chown -R app:app /app/data/runtime
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]

# --workers 1: bộ nhớ phiên nằm trong RAM của tiến trình.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]


FROM base AS ml

USER root
COPY requirements-ml.txt ./
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-ml.txt
USER app
