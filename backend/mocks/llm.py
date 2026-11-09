"""Mock LLM: câu đồng cảm theo nhãn, có tham chiếu lịch sử."""

from mocks._util import simulate_latency

_OPENERS = {
    "Anger": "Nghe có vẻ bạn đang rất bực bội.",
    "Disgust": "Có vẻ chuyện này làm bạn thấy khó chịu.",
    "Enjoyment": "Nghe bạn vui mình cũng vui lây.",
    "Fear": "Mình hiểu là bạn đang lo lắng.",
    "Other": "Mình đang lắng nghe bạn đây.",
    "Sadness": "Mình rất tiếc khi nghe bạn đang buồn.",
    "Surprise": "Nghe bất ngờ thật đấy.",
}

_GOAL_HINTS = {
    "xoa_diu": "Mình sẽ chọn vài bài nhẹ nhàng để xoa dịu bạn.",
    "nang_mood": "Mình sẽ chọn vài bài để nâng tinh thần cho bạn.",
    "tap_trung": "Mình sẽ chọn vài bài giúp bạn tập trung.",
    "giai_toa": "Mình sẽ chọn vài bài để bạn giải tỏa.",
}


def generate_reply(
    text: str,
    emotion: dict,
    arousal: str | None,
    history: list[dict],
    goal: str | None = None,
) -> str:
    simulate_latency()
    label = (emotion or {}).get("label", "Other")
    parts = [_OPENERS.get(label, _OPENERS["Other"])]
    previous = [m["content"] for m in history if m.get("role") == "user"]
    if previous:
        parts.append(f"Lúc nãy bạn có nhắc đến \"{previous[-1][:40]}\", mình vẫn nhớ điều đó.")
    if goal in _GOAL_HINTS:
        parts.append(_GOAL_HINTS[goal])
    parts.append("Bạn muốn kể thêm về chuyện này không?")
    return " ".join(parts)
