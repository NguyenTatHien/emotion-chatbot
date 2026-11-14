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


@pytest.mark.parametrize("variant", VARIANTS)
def test_recommend_is_deterministic(variant):
    a = call(variant, "music", "recommend", "Anger", "high", "giai_toa")
    b = call(variant, "music", "recommend", "Anger", "high", "giai_toa")
    assert a == b


@pytest.mark.parametrize("variant", VARIANTS)
def test_exclude_skips_listed_songs(variant):
    first = call(variant, "music", "recommend", "Sadness", "low", "xoa_diu")
    urls = [s["youtube_url"] for s in first]
    second = call(variant, "music", "recommend", "Sadness", "low", "xoa_diu", exclude=urls)
    assert 3 <= len(second) <= 5
    assert not set(urls) & {s["youtube_url"] for s in second}


@pytest.mark.parametrize("variant", VARIANTS)
def test_exclude_none_or_empty_equals_old_contract(variant):
    base = call(variant, "music", "recommend", "Sadness", "low", "xoa_diu")
    assert call(variant, "music", "recommend", "Sadness", "low", "xoa_diu", exclude=None) == base
    assert call(variant, "music", "recommend", "Sadness", "low", "xoa_diu", exclude=[]) == base


@pytest.mark.parametrize("variant", VARIANTS)
def test_exclude_everything_still_returns_at_least_3(variant):
    from mocks.music import _load_songs

    everything = [row["youtube_url"] for row in _load_songs()]
    songs = call(variant, "music", "recommend", "Sadness", "low", "xoa_diu", exclude=everything)
    assert 3 <= len(songs) <= 5


def test_mock_honours_latency(set_env):
    set_env(MOCK_LATENCY_MS=100)
    start = time.perf_counter()
    call("mock", "music", "recommend", "Sadness", None, None)
    assert time.perf_counter() - start >= 0.09
