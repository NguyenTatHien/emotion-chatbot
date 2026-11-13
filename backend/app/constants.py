"""Hằng số dùng chung cho backend."""

LABELS = ["Anger", "Disgust", "Enjoyment", "Fear", "Other", "Sadness", "Surprise"]

# Tên tiếng Việt của nhãn, khớp với frontend (`src/lib/emotion-meta.ts`).
LABELS_VI = {
    "Anger": "Tức giận",
    "Disgust": "Khó chịu",
    "Enjoyment": "Vui vẻ",
    "Fear": "Lo sợ",
    "Other": "Bình thường",
    "Sadness": "Buồn",
    "Surprise": "Ngạc nhiên",
}

GOALS = ["xoa_diu", "nang_mood", "tap_trung", "giai_toa"]

MODULE_NAMES = ["emotion", "speech", "safety", "llm", "music"]

MODES = ["mock", "local", "remote"]

# Mode chỉ dành cho LLM: dùng Gemini API làm nguồn trả lời chính (không cần GPU/Colab).
LLM_ONLY_MODES = ["gemini"]

AROUSAL_LEVELS = ["low", "medium", "high"]

MAX_MESSAGE_CHARS = 1000
MAX_SESSION_TURNS = 200
MAX_SESSIONS = 1000
