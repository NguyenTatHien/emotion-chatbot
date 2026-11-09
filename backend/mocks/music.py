"""Mock gợi ý nhạc đọc từ data/songs.csv."""

import csv
from pathlib import Path

from app.config import get_settings
from mocks._util import simulate_latency

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _load_songs() -> list[dict]:
    path = Path(get_settings().SONGS_CSV)
    if not path.is_absolute():
        path = _BACKEND_ROOT / path
    with path.open(encoding="utf-8", newline="") as f:
        lines = [line for line in f if not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def recommend(label: str, arousal: str | None, goal: str | None, k: int = 5) -> list[dict]:
    simulate_latency()
    songs = _load_songs()

    def score(song: dict) -> int:
        s = 0
        if label in song["emotion_tags"].split("|"):
            s += 2
        if goal and goal in song["goal_tags"].split("|"):
            s += 2
        if arousal and song["energy"] == arousal:
            s += 1
        return s

    ranked = sorted(songs, key=lambda s: -score(s))  # sort ổn định nên kết quả tất định
    limit = max(1, min(k, 5))
    result = []
    for song in ranked[:limit]:
        reasons = []
        if label in song["emotion_tags"].split("|"):
            reasons.append(f"hợp với cảm xúc {label}")
        if goal and goal in song["goal_tags"].split("|"):
            reasons.append("đúng mục tiêu nghe nhạc bạn chọn")
        result.append(
            {
                "title": song["title"],
                "artist": song["artist"],
                "youtube_url": song["youtube_url"],
                "reason": "Bài " + (", ".join(reasons) if reasons else "nhẹ nhàng để thư giãn"),
            }
        )
    return result
