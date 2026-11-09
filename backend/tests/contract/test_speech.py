import pytest

from tests.contract.conftest import VARIANTS, call


@pytest.mark.parametrize("variant", VARIANTS)
def test_transcribe_returns_str(variant, sample_wav):
    assert isinstance(call(variant, "speech", "transcribe", sample_wav), str)


@pytest.mark.parametrize("variant", VARIANTS)
def test_extract_prosody_contract(variant, sample_wav):
    result = call(variant, "speech", "extract_prosody", sample_wav)
    assert result["arousal"] in {"low", "medium", "high"}
    for key in ("pitch_mean", "energy_rms", "speech_rate"):
        assert isinstance(result[key], float | int)
