"""Lưu đánh giá thích/không thích vào file JSONL (không lưu nội dung tin nhắn hay câu trả lời)."""

import asyncio
import csv
import io
import json
from pathlib import Path

from app.config import get_settings

FIELDS = [
    "session_id",
    "turn_id",
    "rating",
    "emotion_label",
    "arousal",
    "goal",
    "safety",
    "llm_backend",
    "created_at",
]

_lock = asyncio.Lock()


def _path() -> Path:
    return Path(get_settings().FEEDBACK_PATH)


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_all(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue  # bỏ qua dòng hỏng, không làm hỏng cả bản xuất
    return rows


async def save(record: dict) -> None:
    """Thêm một dòng; đánh giá mới hơn cho cùng turn_id sẽ thắng khi xuất."""
    async with _lock:
        await asyncio.to_thread(_append, _path(), {k: record.get(k) for k in FIELDS})


async def latest_by_turn() -> list[dict]:
    async with _lock:
        rows = await asyncio.to_thread(_read_all, _path())
    latest: dict[str, dict] = {}
    for row in rows:
        latest[str(row.get("turn_id"))] = row  # dòng sau ghi đè dòng trước
    return list(latest.values())


def _safe_cell(value: object) -> object:
    # Chặn CSV injection: session_id do client tự đặt nên có thể bắt đầu bằng ký tự công thức.
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


async def export_csv() -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(FIELDS)
    for row in await latest_by_turn():
        writer.writerow([_safe_cell(row.get(k)) for k in FIELDS])
    return buf.getvalue()
