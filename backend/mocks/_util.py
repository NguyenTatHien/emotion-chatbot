"""Tiện ích dùng chung cho mock."""

import time

from app.config import get_settings


def simulate_latency() -> None:
    ms = get_settings().MOCK_LATENCY_MS
    if ms > 0:
        time.sleep(ms / 1000)
