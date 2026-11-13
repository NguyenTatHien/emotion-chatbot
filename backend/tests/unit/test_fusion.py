"""Late fusion: công thức, điều kiện áp dụng, cấu hình FUSION_ALPHA."""

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.constants import LABELS
from app.fusion import apply_fusion, fuse


def probs_of(**values: float) -> dict[str, float]:
    return {k: values.get(k, 0.0) for k in LABELS}


SAD_ANGER = probs_of(Sadness=0.45, Anger=0.30, Other=0.25)


def test_high_arousal_pulls_toward_anger_but_tie_keeps_text_label():
    out, applied = apply_fusion({"label": "Sadness", "probs": SAD_ANGER}, "high", 0.2, True)
    assert applied is True
    assert out["probs"]["Sadness"] == pytest.approx(0.391, abs=0.001)
    assert out["probs"]["Anger"] == pytest.approx(0.391, abs=0.001)
    assert out["probs"]["Other"] == pytest.approx(0.217, abs=0.001)
    assert sum(out["probs"].values()) == pytest.approx(1.0)
    assert out["label"] == "Sadness"
    assert out["label_text"] == "Sadness"
    assert out["probs_text"] == SAD_ANGER


def test_low_arousal_reinforces_sadness():
    out, applied = apply_fusion({"label": "Sadness", "probs": SAD_ANGER}, "low", 0.2, True)
    assert applied is True
    assert out["label"] == "Sadness"
    assert out["probs"]["Sadness"] > 0.45


def test_very_confident_text_is_not_flipped():
    probs = probs_of(Enjoyment=0.98, Sadness=0.02)
    out, _ = apply_fusion({"label": "Enjoyment", "probs": probs}, "low", 0.2, True)
    assert out["label"] == "Enjoyment"


def test_disgust_keeps_unit_weight():
    probs = probs_of(Disgust=0.5, Anger=0.5)
    fused = fuse(probs, "high", 0.2)
    assert fused["Anger"] > fused["Disgust"]
    assert fused["Disgust"] == pytest.approx(0.5 / (0.5 + 0.5 * 1.2))


def test_close_labels_can_flip():
    probs = probs_of(Sadness=0.40, Anger=0.35, Other=0.25)
    out, applied = apply_fusion({"label": "Sadness", "probs": probs}, "high", 0.2, True)
    assert applied is True
    assert out["label"] == "Anger"
    assert out["label_text"] == "Sadness"


def test_fuse_sums_to_one_and_keeps_all_labels():
    fused = fuse(SAD_ANGER, "low", 0.3)
    assert set(fused) == set(LABELS)
    assert sum(fused.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("arousal", "alpha", "from_module"),
    [("medium", 0.2, True), (None, 0.2, True), ("high", 0.0, True), ("high", 0.2, False)],
)
def test_not_applied_returns_input_unchanged(arousal, alpha, from_module):
    emotion = {"label": "Sadness", "probs": SAD_ANGER}
    out, applied = apply_fusion(emotion, arousal, alpha, from_module)
    assert applied is False
    assert out is emotion
    assert "label_text" not in out


def test_alpha_default_and_validation():
    assert Settings().FUSION_ALPHA == 0.2
    assert Settings(FUSION_ALPHA=0).FUSION_ALPHA == 0
    assert Settings(FUSION_ALPHA=0.5).FUSION_ALPHA == 0.5
    with pytest.raises(ValidationError, match="FUSION_ALPHA"):
        Settings(FUSION_ALPHA=0.9)
    with pytest.raises(ValidationError, match="FUSION_ALPHA"):
        Settings(FUSION_ALPHA=-0.1)
