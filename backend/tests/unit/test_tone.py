"""Bảng giọng điệu `app.tone.choose_tone` (design D1)."""

import pytest

from app.constants import LABELS
from app.tone import TONES, choose_tone


def emo(label, p=0.7):
    probs = dict.fromkeys(LABELS, (1 - p) / (len(LABELS) - 1))
    probs[label] = p
    return {"label": label, "probs": probs}


@pytest.mark.parametrize(
    ("label", "arousal", "key"),
    [
        ("Sadness", "high", "sad_high"),
        ("Sadness", "medium", "sad"),
        ("Sadness", "low", "sad"),
        ("Sadness", None, "sad"),
        ("Fear", None, "fear"),
        ("Fear", "high", "fear"),
        ("Anger", None, "anger"),
        ("Disgust", None, "disgust"),
        ("Enjoyment", None, "joy"),
        ("Surprise", None, "surprise"),
        ("Other", None, "neutral"),
    ],
)
def test_every_row_of_the_table(label, arousal, key):
    tone = choose_tone(emo(label), arousal)
    assert tone["key"] == key
    assert tone["text"] == TONES[key]


def test_sad_with_high_arousal():
    assert choose_tone(emo("Sadness", 0.7), "high")["key"] == "sad_high"


def test_anger_does_not_tell_user_to_calm_down():
    tone = choose_tone(emo("Anger", 0.8), None)
    assert tone["key"] == "anger"
    assert "bình tĩnh đi" not in tone["text"]


def test_uncertain_when_top_probability_below_half():
    assert choose_tone(emo("Sadness", 0.42), "high")["key"] == "uncertain"
    assert choose_tone(emo("Anger", 0.42), None)["key"] == "uncertain"


def test_exactly_half_is_not_uncertain():
    assert choose_tone(emo("Fear", 0.5), None)["key"] == "fear"


def test_uniform_fallback_emotion_is_uncertain():
    uniform = {"label": "Other", "probs": dict.fromkeys(LABELS, 1 / len(LABELS))}
    assert choose_tone(uniform, None)["key"] == "uncertain"


def test_texts_are_short_vietnamese_instructions():
    for text in TONES.values():
        assert 0 < len(text.split()) < 25
