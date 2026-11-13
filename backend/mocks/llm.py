"""Mock LLM: câu đồng cảm theo nhãn, có tham chiếu lịch sử, kèm thẻ nhạc tất định."""

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


# Cụm từ xin nhạc: thấy một trong các cụm này thì mock gắn thẻ CO.
_MUSIC_REQUESTS = ("nghe nhạc", "bài hát", "bài nào", "playlist", "mở nhạc")
_MUSIC_LABELS = ("Sadness", "Fear")


def _music_tag(text: str, label: str, history: list[dict]) -> str:
    """Thẻ nhạc tất định (chỉ để dev/test, không phải hành vi sản phẩm)."""
    lowered = (text or "").lower()
    asked = any(phrase in lowered for phrase in _MUSIC_REQUESTS)
    has_user_turn = any(m.get("role") == "user" for m in history)
    if asked or (label in _MUSIC_LABELS and has_user_turn):
        return "[NHAC:CO]"
    return "[NHAC:KHONG]"


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
    return f"{_music_tag(text, label, history)}\n{' '.join(parts)}"
