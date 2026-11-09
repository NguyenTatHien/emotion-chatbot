import pytest

from tests.contract.conftest import VARIANTS, call

EMOTION = {
    "label": "Sadness",
    "probs": {
        "Anger": 0.05,
        "Disgust": 0.05,
        "Enjoyment": 0.05,
        "Fear": 0.05,
        "Other": 0.1,
        "Sadness": 0.6,
        "Surprise": 0.1,
    },
}


@pytest.mark.parametrize("variant", VARIANTS)
def test_reply_is_non_empty_str(variant):
    reply = call(variant, "llm", "generate_reply", "mình buồn quá", EMOTION, None, [])
    assert isinstance(reply, str) and reply.strip()


@pytest.mark.parametrize("variant", VARIANTS)
def test_reply_with_history_arousal_goal(variant):
    history = [
        {"role": "user", "content": "chào bạn"},
        {"role": "assistant", "content": "Chào bạn, mình nghe đây."},
    ]
    reply = call(
        variant, "llm", "generate_reply", "mình mệt", EMOTION, "low", history, goal="xoa_diu"
    )
    assert isinstance(reply, str) and reply.strip()


def test_mock_references_history():
    history = [
        {"role": "user", "content": "chuyện hôm qua"},
        {"role": "assistant", "content": "ok"},
    ]
    reply = call("mock", "llm", "generate_reply", "mình mệt", EMOTION, None, history)
    assert "chuyện hôm qua" in reply
