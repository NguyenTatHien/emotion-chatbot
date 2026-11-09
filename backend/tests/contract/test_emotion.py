import math

import pytest

from tests.contract.conftest import VARIANTS, call, load

LABELS = ["Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise"]


def _check(result):
    assert isinstance(result, dict)
    assert result["label"] in LABELS
    assert set(result["probs"]) == set(LABELS)
    assert all(isinstance(v, float) and 0 <= v <= 1 for v in result["probs"].values())
    assert math.isclose(sum(result["probs"].values()), 1.0, abs_tol=1e-6)


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("text", ["mình buồn quá", "hôm nay vui ghê", "", "😭😭😭", "   "])
def test_predict_emotion_contract(variant, text):
    _check(call(variant, "emotion", "predict_emotion", text))


def test_mock_reflects_keywords():
    assert call("mock", "emotion", "predict_emotion", "mình buồn quá")["label"] == "Sadness"
    assert call("mock", "emotion", "predict_emotion", "tức giận quá")["label"] == "Anger"
    assert call("mock", "emotion", "predict_emotion", "ừm")["label"] == "Other"


@pytest.mark.parametrize("variant", VARIANTS)
def test_labels_constant(variant):
    assert load(variant, "emotion").LABELS == LABELS
