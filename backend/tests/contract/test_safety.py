import pytest

from tests.contract.conftest import VARIANTS, call


@pytest.mark.parametrize("variant", VARIANTS)
def test_safe_text(variant):
    result = call(variant, "safety", "check_safety", "hôm nay mình đi học về mệt quá")
    assert result["risk"] is False


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("text", ["mình muốn chết", "tôi định tự tử", "toi khong muon song nua"])
def test_risky_text(variant, text):
    result = call(variant, "safety", "check_safety", text)
    assert result["risk"] is True
    assert isinstance(result["message"], str) and result["message"].strip()


@pytest.mark.parametrize("variant", VARIANTS)
def test_empty_text_does_not_crash(variant):
    result = call(variant, "safety", "check_safety", "")
    assert isinstance(result["risk"], bool)
