"""Module gợi ý nhạc — hợp đồng của Người 5.

Bản này do Hiển viết thay Người 5, cần Người 5 review trước khi coi là bản chính thức.

Chiến lược theo nội dung, không học từ dữ liệu:
- năng lượng đích suy từ mục tiêu và cảm xúc (nguyên tắc iso: khớp trước, nâng sau);
- chấm điểm từng bài theo cảm xúc, mục tiêu, năng lượng và thể loại;
- mỗi nghệ sĩ chính tối đa 1 bài, bỏ qua bài trong `exclude`, kết quả tất định.

KHÔNG import thư viện nặng ở đầu file; import bên trong thân hàm.
"""

import csv
import re
from collections.abc import Iterable
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_MAX_K = 5
_MIN_SONGS = 3

_ENERGY_ORDER = {"low": 0, "medium": 1, "high": 2}

# D1: năng lượng đích theo mục tiêu; khi không có mục tiêu thì theo cảm xúc.
_GOAL_ENERGY = {"xoa_diu": "low", "tap_trung": "low", "nang_mood": "medium", "giai_toa": "high"}
_LABEL_ENERGY = {
    "Sadness": "low",
    "Fear": "low",
    "Anger": "high",
    "Disgust": "high",
    "Enjoyment": "medium",
    "Surprise": "medium",
}

# D2: thể loại hợp với mục tiêu (tap_trung xét riêng theo `language == instrumental`).
_GOAL_GENRES = {
    "xoa_diu": {"ballad", "indie"},
    "giai_toa": {"rock", "rap"},
    "nang_mood": {"pop"},
}

_EMOTION_REASON = {
    "Sadness": "hợp với tâm trạng buồn",
    "Fear": "giúp dịu bớt lo lắng",
    "Anger": "giúp xả bớt bực bội",
    "Disgust": "giúp đổi không khí",
    "Enjoyment": "hợp với tâm trạng vui",
    "Surprise": "hợp với cảm giác bất ngờ",
}
_GOAL_REASON = {
    "xoa_diu": "đúng mục tiêu xoa dịu",
    "nang_mood": "đúng mục tiêu nâng tâm trạng",
    "tap_trung": "đúng mục tiêu tập trung",
    "giai_toa": "đúng mục tiêu giải toả",
}
_ENERGY_REASON = {
    "low": "nhịp chậm, êm tai",
    "medium": "nhịp vừa phải, dễ nghe",
    "high": "nhịp mạnh để xả",
}
_DEFAULT_REASON = "nhẹ nhàng để thư giãn"

_ARTIST_SPLIT = re.compile(r"\s+(?:ft\.?|feat\.?)\s+|\s+x\s+|,", re.IGNORECASE)

# Cache CSV theo (đường dẫn, mtime) để không đọc lại mỗi lượt.
_cache: dict[str, tuple[float, list[dict]]] = {}


def _main_artist(artist: str) -> str:
    """Nghệ sĩ chính = phần trước "ft." / " x " / ",", viết thường."""
    return _ARTIST_SPLIT.split(artist, maxsplit=1)[0].strip().lower()


def _csv_path() -> Path:
    from app.config import get_settings

    path = Path(get_settings().SONGS_CSV)
    return path if path.is_absolute() else _BACKEND_ROOT / path


def _load_songs() -> list[dict]:
    path = _csv_path()
    key = str(path)
    mtime = path.stat().st_mtime
    cached = _cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    with path.open(encoding="utf-8", newline="") as f:
        lines = [line for line in f if not line.lstrip().startswith("#")]
    songs = []
    for row in csv.DictReader(lines):
        songs.append(
            {
                **row,
                "emotions": frozenset(row["emotion_tags"].split("|")),
                "goals": frozenset(row["goal_tags"].split("|")),
                "main_artist": _main_artist(row["artist"]),
            }
        )
    _cache[key] = (mtime, songs)
    return songs


def _target_energy(label: str, arousal: str | None, goal: str | None) -> str:
    if goal in _GOAL_ENERGY:
        return _GOAL_ENERGY[goal]
    if label in _LABEL_ENERGY:
        return _LABEL_ENERGY[label]
    return arousal if arousal in _ENERGY_ORDER else "medium"


def _genre_fits(song: dict, goal: str | None) -> bool:
    if goal == "tap_trung":
        return song["language"] == "instrumental"
    return song["genre"] in _GOAL_GENRES.get(goal or "", ())


def _score(song: dict, label: str, goal: str | None, target: str) -> int:
    s = 0
    if label in song["emotions"]:
        s += 3
    if goal and goal in song["goals"]:
        s += 3
    gap = abs(_ENERGY_ORDER.get(song["energy"], 1) - _ENERGY_ORDER[target])
    s += {0: 2, 1: 1}.get(gap, 0)
    if _genre_fits(song, goal):
        s += 1
    if goal == "tap_trung" and song["language"] != "instrumental":
        s -= 2
    return s


def _reason(song: dict, label: str, goal: str | None, target: str) -> str:
    parts = []
    if label in song["emotions"] and label in _EMOTION_REASON:
        parts.append(_EMOTION_REASON[label])
    focus = goal == "tap_trung" and _genre_fits(song, goal)
    if focus:
        # Câu cụ thể thay cho câu mục tiêu chung để không nói lặp.
        parts.append("nhạc không lời giúp tập trung")
    elif goal and goal in song["goals"]:
        parts.append(_GOAL_REASON[goal])
    if _genre_fits(song, goal) and not focus:
        if goal == "xoa_diu":
            parts.append(f"{song['genre']} nhẹ nhàng, dễ chịu")
        else:
            parts.append(f"thể loại {song['genre']} hợp mục tiêu")
    if song["energy"] == target:
        parts.append(_ENERGY_REASON[target])
    return "Bài " + (", ".join(parts[:2]) if parts else _DEFAULT_REASON)


def recommend(
    label: str,
    arousal: str | None,
    goal: str | None,
    k: int = 5,
    exclude: Iterable[str] | None = None,
) -> list[dict]:
    """Gợi ý bài hát theo cảm xúc, mức kích động và mục tiêu nghe nhạc.

    Đầu vào: label (1 trong 7 nhãn), arousal ("low"|"medium"|"high"|None),
             goal ("xoa_diu"|"nang_mood"|"tap_trung"|"giai_toa"|None), k (số bài tối đa,
             kẹp trong [1, 5]), exclude (các `youtube_url` cần tránh, None = rỗng).
    Đầu ra: danh sách 3 đến k phần tử (k < 3 thì đúng k bài)
      {"title": str, "artist": str, "youtube_url": str, "reason": str}
    Mỗi nghệ sĩ chính tối đa 1 bài; bài trong `exclude` chỉ được dùng để bù cho đủ 3 bài.
    """
    limit = max(1, min(k, _MAX_K))
    minimum = min(_MIN_SONGS, limit)
    skipped = set(exclude or ())
    target = _target_energy(label, arousal, goal)

    scored = [(_score(s, label, goal, target), s) for s in _load_songs()]
    # Điểm giảm dần, hoà thì theo title: không phụ thuộc thứ tự dòng trong file.
    scored.sort(key=lambda item: (-item[0], item[1]["title"], item[1]["youtube_url"]))

    def pick(pool: list[tuple[int, dict]], chosen: list[tuple[int, dict]], cap: int) -> None:
        artists = {s["main_artist"] for _, s in chosen}
        for score, song in pool:
            if len(chosen) >= cap:
                return
            if song["main_artist"] in artists:
                continue
            artists.add(song["main_artist"])
            chosen.append((score, song))

    chosen: list[tuple[int, dict]] = []
    pick([item for item in scored if item[1]["youtube_url"] not in skipped], chosen, limit)
    # Bỏ bài điểm <= 0 nếu đã đủ tối thiểu.
    positive = [item for item in chosen if item[0] > 0]
    chosen = positive if len(positive) >= minimum else chosen[: max(minimum, len(positive))]
    if len(chosen) < minimum:
        # Catalog gần cạn vì exclude: thà lặp bài còn hơn trả quá ít bài.
        pick([item for item in scored if item[1]["youtube_url"] in skipped], chosen, minimum)

    return [
        {
            "title": song["title"],
            "artist": song["artist"],
            "youtube_url": song["youtube_url"],
            "reason": _reason(song, label, goal, target),
        }
        for _, song in chosen
    ]
