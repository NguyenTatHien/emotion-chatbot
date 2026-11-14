"""Module gợi ý nhạc `modules.music`: mọi scenario trong spec music-recommendation."""

import csv
import itertools
import os
from pathlib import Path

import pytest

from app.config import reload_settings
from app.constants import LABELS
from modules import music

GOALS = ["xoa_diu", "nang_mood", "tap_trung", "giai_toa", None]
CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "songs.csv"


@pytest.fixture(scope="module")
def catalog() -> dict[str, dict]:
    with CATALOG_PATH.open(encoding="utf-8", newline="") as f:
        lines = [line for line in f if not line.lstrip().startswith("#")]
    return {row["youtube_url"]: row for row in csv.DictReader(lines)}


def energies(songs, catalog):
    return [catalog[s["youtube_url"]]["energy"] for s in songs]


# --- Chọn bài theo mục tiêu và cảm xúc ---


def test_focus_prefers_instrumental(catalog):
    songs = music.recommend("Other", None, "tap_trung")
    instrumental = [s for s in songs if catalog[s["youtube_url"]]["language"] == "instrumental"]
    assert len(instrumental) >= 3


def test_sad_and_soothing_picks_low_energy(catalog):
    found = energies(music.recommend("Sadness", "low", "xoa_diu"), catalog)
    assert set(found) <= {"low", "medium"}
    assert found.count("low") > len(found) / 2


def test_release_picks_high_energy(catalog):
    found = energies(music.recommend("Anger", "high", "giai_toa"), catalog)
    assert found.count("high") > len(found) / 2


def test_result_shape_and_count():
    songs = music.recommend("Enjoyment", None, None)
    assert 3 <= len(songs) <= 5
    for song in songs:
        assert set(song) == {"title", "artist", "youtube_url", "reason"}
        assert song["youtube_url"].startswith("https://")


@pytest.mark.parametrize(("k", "expected"), [(0, 1), (1, 1), (2, 2), (3, 3), (5, 5), (9, 5)])
def test_k_is_clamped_between_1_and_5(k, expected):
    assert len(music.recommend("Sadness", "low", "xoa_diu", k)) == expected


def test_target_energy_follows_emotion_when_no_goal():
    assert music._target_energy("Sadness", "high", None) == "low"
    assert music._target_energy("Fear", None, None) == "low"
    assert music._target_energy("Anger", "low", None) == "high"
    assert music._target_energy("Disgust", None, None) == "high"
    assert music._target_energy("Enjoyment", "low", None) == "medium"
    assert music._target_energy("Surprise", "high", None) == "medium"


def test_other_without_goal_uses_arousal_or_medium():
    assert music._target_energy("Other", "high", None) == "high"
    assert music._target_energy("Other", "low", None) == "low"
    assert music._target_energy("Other", None, None) == "medium"


def test_goal_decides_target_energy_over_emotion():
    assert music._target_energy("Anger", "high", "xoa_diu") == "low"
    assert music._target_energy("Sadness", "low", "nang_mood") == "medium"
    assert music._target_energy("Sadness", "low", "tap_trung") == "low"
    assert music._target_energy("Sadness", "low", "giai_toa") == "high"


def test_deterministic():
    for label, goal in itertools.product(sorted(LABELS), GOALS):
        assert music.recommend(label, "low", goal) == music.recommend(label, "low", goal)


# --- Đa dạng nghệ sĩ ---


def test_no_repeated_main_artist_in_any_combination():
    for label, goal in itertools.product(sorted(LABELS), GOALS):
        artists = [music._main_artist(s["artist"]) for s in music.recommend(label, None, goal)]
        assert len(artists) == len(set(artists)), (label, goal)


@pytest.mark.parametrize(
    ("artist", "main"),
    [
        ("Đen ft. Biên", "đen"),
        ("Đen x JustaTee", "đen"),
        ("W/n ft. Nâu, Dươngg, 267", "w/n"),
        ("Hoàng Dũng, Tăng Duy Tân", "hoàng dũng"),
        ("Taylor Swift", "taylor swift"),
        ("Katrina & The Waves", "katrina & the waves"),
    ],
)
def test_main_artist_extraction(artist, main):
    assert music._main_artist(artist) == main


# --- Không lặp bài nhờ exclude ---


def test_three_consecutive_turns_do_not_repeat():
    seen: set[str] = set()
    for _ in range(3):
        urls = [
            s["youtube_url"]
            for s in music.recommend("Sadness", "low", "xoa_diu", exclude=sorted(seen))
        ]
        assert not seen & set(urls)
        seen.update(urls)


def test_exclude_accepts_any_iterable():
    first = music.recommend("Sadness", "low", "xoa_diu")
    urls = (s["youtube_url"] for s in first)
    second = music.recommend("Sadness", "low", "xoa_diu", exclude=urls)
    assert not {s["youtube_url"] for s in first} & {s["youtube_url"] for s in second}


def test_exclude_exhausted_catalog_tops_up_to_3(catalog):
    songs = music.recommend("Sadness", "low", "xoa_diu", exclude=list(catalog))
    assert len(songs) == 3


def test_backward_compatible_without_exclude():
    assert music.recommend("Sadness", "low", "xoa_diu") == music.recommend(
        "Sadness", "low", "xoa_diu", exclude=None
    )


# --- Lý do tiếng Việt ---


def test_reasons_start_with_bai_and_have_no_english_label():
    for label, goal in itertools.product(sorted(LABELS), GOALS):
        for song in music.recommend(label, None, goal):
            assert song["reason"].startswith("Bài "), song["reason"]
            assert not any(name in song["reason"] for name in LABELS), song["reason"]


def test_sadness_reasons_mention_matched_criteria():
    for song in music.recommend("Sadness", "low", "xoa_diu"):
        assert "buồn" in song["reason"] or "xoa dịu" in song["reason"]


def test_focus_reason_mentions_instrumental():
    reasons = [s["reason"] for s in music.recommend("Other", None, "tap_trung")]
    assert all("không lời" in r for r in reasons)


# --- Cache CSV ---


def test_csv_is_cached_until_file_changes(tmp_path, monkeypatch):
    path = tmp_path / "songs.csv"
    path.write_text(CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("SONGS_CSV", str(path))
    reload_settings()
    first = music._load_songs()
    assert music._load_songs() is first
    stat = path.stat()
    os.utime(path, (stat.st_atime, stat.st_mtime + 5))
    assert music._load_songs() is not first
