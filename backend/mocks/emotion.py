"""Mock cảm xúc tất định theo từ khóa."""

import re

from app.constants import LABELS
from mocks._util import simulate_latency

_KEYWORDS = [
    ("Sadness", ["buồn", "mệt", "chán", "khóc", "cô đơn", "thất vọng", "tệ quá"]),
    ("Enjoyment", ["vui", "hạnh phúc", "tuyệt", "yêu đời", "phấn khởi", "thích quá"]),
    ("Anger", ["giận", "bực", "tức", "điên", "ghét"]),
    ("Fear", ["sợ", "lo", "hoảng", "run", "căng thẳng"]),
    ("Disgust", ["ghê", "kinh", "tởm", "khó chịu"]),
    ("Surprise", ["bất ngờ", "wow", "ngạc nhiên", "không ngờ"]),
]

_PATTERNS = [
    (label, [re.compile(rf"(?<!\w){re.escape(w)}(?!\w)") for w in words])
    for label, words in _KEYWORDS
]


def predict_emotion(text: str) -> dict:
    simulate_latency()
    lowered = (text or "").lower()
    label = "Other"
    for candidate, patterns in _PATTERNS:
        if any(p.search(lowered) for p in patterns):
            label = candidate
            break
    rest = 0.4 / (len(LABELS) - 1)
    probs = {name: (0.6 if name == label else rest) for name in LABELS}
    return {"label": label, "probs": probs}
