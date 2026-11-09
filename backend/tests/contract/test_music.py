import time

import pytest

from tests.contract.conftest import VARIANTS, call

FIELDS = {"title", "artist", "youtube_url", "reason"}


@pytest.mark.parametrize("variant", VARIANTS)
def test_recommend_contract(variant):
    songs = call(variant, "music", "recommend", "Sadness", "low", "xoa_diu")
    assert 1 <= len(songs) <= 5
    for song in songs:
        assert FIELDS <= set(song)
        assert song["youtube_url"].startswith("https://")


@pytest.mark.parametrize("variant", VARIANTS)
def test_recommend_respects_k(variant):
    assert len(call(variant, "music", "recommend", "Enjoyment", None, None, k=3)) <= 3


def test_mock_returns_3_to_5_with_youtube_urls():
    songs = call("mock", "music", "recommend", "Sadness", "low", "xoa_diu")
    assert 3 <= len(songs) <= 5
    assert all(s["youtube_url"].startswith("https://www.youtube.com/watch?v=") for s in songs)


def test_mock_is_deterministic():
    a = call("mock", "music", "recommend", "Anger", "high", "giai_toa")
    b = call("mock", "music", "recommend", "Anger", "high", "giai_toa")
    assert a == b


def test_mock_honours_latency(set_env):
    set_env(MOCK_LATENCY_MS=100)
    start = time.perf_counter()
    call("mock", "music", "recommend", "Sadness", None, None)
    assert time.perf_counter() - start >= 0.09
