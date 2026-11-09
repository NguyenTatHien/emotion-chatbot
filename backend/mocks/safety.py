"""Mock an toàn theo cụm từ khóa."""

from app.fallbacks import keyword_safety, safety_message
from mocks._util import simulate_latency


def check_safety(text: str) -> dict:
    simulate_latency()
    if keyword_safety(text):
        return {"risk": True, "message": safety_message()}
    return {"risk": False, "message": None}
