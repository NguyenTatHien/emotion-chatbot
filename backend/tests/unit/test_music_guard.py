"""Chốt chặn thẻ [NHAC:CO] và lý do bài hát tiếng Việt của mock music."""

import pytest

from app.music_guard import accept_music_tag, asks_for_music
from mocks import music


@pytest.mark.parametrize(
    "text",
    [
        "có bài nào nghe cho vui không",
        "mở nhạc gì nhẹ nhẹ đi",
        "co bai hat nao hay khong",
        "gợi ý bài để học bài với",
        "cho mình cái playlist lofi",
    ],
)
def test_detects_music_requests(text):
    assert asks_for_music(text)


@pytest.mark.parametrize(
    "text",
    ["Mình tên Hiển, tuần sau thi môn NLP", "chào bạn", "bố mình là nhạc sĩ đó"],
)
def test_ignores_normal_sentences(text):
    assert not asks_for_music(text)


def test_neutral_turn_without_request_is_blocked():
    assert not accept_music_tag("Mình tên Hiển, tuần sau thi môn NLP", "Other", "module")
    assert not accept_music_tag("hôm nay vui ghê", "Enjoyment", "module")


@pytest.mark.parametrize("label", ["Sadness", "Fear", "Anger", "Disgust"])
def test_negative_turn_is_accepted(label):
    assert accept_music_tag("mình mệt mỏi quá", label, "module")


def test_request_is_accepted_whatever_the_emotion():
    assert accept_music_tag("có bài nào nghe cho vui không", "Enjoyment", "module")


def test_fallback_emotion_trusts_the_llm():
    assert accept_music_tag("chào bạn", "Other", "fallback")


def test_mock_music_reasons_are_vietnamese():
    for label in ("Sadness", "Other", "Enjoyment"):
        for song in music.recommend(label, None, None, 5):
            assert label not in song["reason"]
            assert song["reason"].startswith("Bài ")
