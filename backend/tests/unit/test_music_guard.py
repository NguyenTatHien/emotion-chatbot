"""Chốt chặn thẻ [NHAC:CO] và lý do bài hát tiếng Việt của mock music."""

import pytest

from app.music_guard import accept_music_tag, asks_for_music, check_music_tag
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
def test_second_negative_turn_is_accepted(label):
    assert accept_music_tag("mình mệt mỏi quá", label, "module", prev_label="Sadness")


@pytest.mark.parametrize("prev", [None, "Other", "Enjoyment"])
def test_first_negative_turn_listens_first(prev):
    assert check_music_tag("mình buồn quá", "Sadness", "module", prev_label=prev) == (
        False,
        "first",
    )


def test_cooldown_after_music_turn():
    result = check_music_tag(
        "mai thi rồi mình sợ lắm", "Fear", "module", prev_label="Anger", prev_had_music=True
    )
    assert result == (False, "cooldown")
    # Xin nhạc thì bỏ qua thời gian nghỉ.
    assert check_music_tag(
        "có bài nào khác không", "Fear", "module", prev_label="Anger", prev_had_music=True
    ) == (True, None)


def test_neutral_reason_code():
    assert check_music_tag("Mình tên Hiển", "Other", "module", prev_label="Sadness") == (
        False,
        "neutral",
    )


def test_request_is_accepted_whatever_the_emotion():
    assert accept_music_tag("có bài nào nghe cho vui không", "Enjoyment", "module")


def test_fallback_emotion_trusts_the_llm():
    assert accept_music_tag("chào bạn", "Other", "fallback")


def test_mock_music_reasons_are_vietnamese():
    for label in ("Sadness", "Other", "Enjoyment"):
        for song in music.recommend(label, None, None, 5):
            assert label not in song["reason"]
            assert song["reason"].startswith("Bài ")


def test_music_lead_by_goal_then_emotion():
    from app.pipeline import DEFAULT_MUSIC_LEAD, music_lead

    assert music_lead(False, "tap_trung", "Sadness") is None
    assert music_lead(True, "tap_trung", "Sadness") == "Vài bài giúp bạn tập trung"
    assert music_lead(True, None, "Anger") == "Vài bài nhịp mạnh để xả bớt"
    assert music_lead(True, None, "Other") == DEFAULT_MUSIC_LEAD


def test_with_music_note_appends_to_context_pair():
    from app import memory

    history = [
        {"role": "user", "content": memory.CONTEXT_HEADER + "\nGiọng điệu nên dùng: dịu."},
        {"role": "assistant", "content": memory.CONTEXT_ACK},
    ]
    out = memory.with_music_note(history, [{"title": "A", "artist": "X"}])
    assert out[0]["content"].endswith("Bài sẽ gợi ý kèm câu trả lời: A – X")
    assert history[0]["content"].endswith("dịu.")  # không sửa bản gốc
    assert memory.with_music_note(history, []) is history


def test_prompts_explain_music_note():
    from app import gemini
    from modules import llm

    assert "Bài sẽ gợi ý kèm câu trả lời" in gemini.SYSTEM_PROMPT
    assert "Bài sẽ gợi ý kèm câu trả lời" in llm._MUSIC_TAG_RULES
