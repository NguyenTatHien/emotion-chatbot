"""Đánh giá gợi ý nhạc: module `local` so với mock, trên mọi tổ hợp đầu vào.

Chạy trong `backend/`:
    python -m app.tools.eval_music

Duyệt 7 nhãn x (4 mục tiêu + không mục tiêu) x arousal (None, low, high) và in:
- độ phủ: tỉ lệ tổ hợp có >= 3 bài khớp cảm xúc hoặc mục tiêu theo nhãn trong CSV;
- đa dạng: trung bình số nghệ sĩ chính khác nhau / số bài;
- lặp bài: mô phỏng 3 lượt liên tiếp cùng tổ hợp (truyền `exclude` dồn dần), đếm số bài
  đã xuất hiện ở lượt trước.
Luôn thoát với mã 0 (đây là công cụ đo, không phải cổng chặn).
"""

import itertools
import sys
from collections.abc import Callable
from unittest import mock

from app.constants import LABELS

GOALS = ["xoa_diu", "nang_mood", "tap_trung", "giai_toa", None]
AROUSALS = [None, "low", "high"]
TURNS = 3
MIN_MATCHED = 3


def combos() -> list[tuple[str, str | None, str | None]]:
    """Mọi tổ hợp (label, arousal, goal)."""
    return [(label, a, g) for label, g, a in itertools.product(sorted(LABELS), GOALS, AROUSALS)]


def evaluate(recommend: Callable, catalog: dict[str, dict], main_artist: Callable) -> dict:
    """Chạy `recommend` trên mọi tổ hợp; `catalog` là {youtube_url: dòng CSV}."""
    covered = 0
    diversity: list[float] = []
    repeats = 0
    repeat_combos = 0
    for label, arousal, goal in combos():
        songs = recommend(label, arousal, goal, 5)
        matched = sum(
            1
            for s in songs
            if label in catalog[s["youtube_url"]]["emotion_tags"].split("|")
            or (goal and goal in catalog[s["youtube_url"]]["goal_tags"].split("|"))
        )
        covered += matched >= MIN_MATCHED
        if songs:
            artists = {main_artist(s["artist"]) for s in songs}
            diversity.append(len(artists) / len(songs))

        seen: set[str] = set()
        combo_repeats = 0
        for _ in range(TURNS):
            turn = recommend(label, arousal, goal, 5, exclude=sorted(seen))
            urls = [s["youtube_url"] for s in turn]
            combo_repeats += sum(url in seen for url in urls)
            seen.update(urls)
        repeats += combo_repeats
        repeat_combos += combo_repeats > 0
    total = len(combos())
    return {
        "combos": total,
        "coverage": covered / total,
        "diversity": sum(diversity) / len(diversity) if diversity else 0.0,
        "repeats": repeats,
        "repeat_combos": repeat_combos,
    }


def format_report(results: dict[str, dict]) -> str:
    lines = [
        f"{'Bản':<8} {'Tổ hợp':>7} {'Độ phủ':>8} {'Đa dạng nghệ sĩ':>16} "
        f"{'Bài lặp / ' + str(TURNS) + ' lượt':>16} {'Tổ hợp có lặp':>14}",
        "-" * 75,
    ]
    for name, r in results.items():
        lines.append(
            f"{name:<8} {r['combos']:>7} {r['coverage']:>8.3f} {r['diversity']:>16.3f} "
            f"{r['repeats']:>16} {r['repeat_combos']:>14}"
        )
    lines += [
        "",
        "mock-cũ: mock không dùng exclude (mốc trước khi có hợp đồng mới).",
        f"Độ phủ: tỉ lệ tổ hợp có >= {MIN_MATCHED} bài khớp cảm xúc hoặc mục tiêu "
        "(theo nhãn gắn tay trong songs.csv).",
        f"Bài lặp: tổng số bài xuất hiện lại ở lượt sau khi mô phỏng {TURNS} lượt "
        "liên tiếp cùng tổ hợp, có truyền exclude dồn dần.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from mocks import music as mock_music
    from modules import music as local_music

    catalog = {row["youtube_url"]: row for row in mock_music._load_songs()}
    with mock.patch.object(mock_music, "simulate_latency", lambda: None):
        results = {
            "module": evaluate(local_music.recommend, catalog, local_music._main_artist),
            "mock": evaluate(mock_music.recommend, catalog, local_music._main_artist),
            # Mock bỏ qua exclude = hành vi trước khi có hợp đồng mới (mốc so sánh).
            "mock-cũ": evaluate(
                lambda label, arousal, goal, k, exclude=None: mock_music.recommend(
                    label, arousal, goal, k
                ),
                catalog,
                local_music._main_artist,
            ),
        }
    print(format_report(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
