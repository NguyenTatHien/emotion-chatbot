"""Bộ nhớ phiên trong RAM (mất khi restart; chạy uvicorn với --workers 1)."""

import asyncio
from collections import OrderedDict, deque

from app.constants import MAX_SESSION_TURNS, MAX_SESSIONS
from app.schemas import SessionTurn


class SessionStore:
    def __init__(self, max_turns: int = MAX_SESSION_TURNS, max_sessions: int = MAX_SESSIONS):
        self._max_turns = max_turns
        self._max_sessions = max_sessions
        self._sessions: OrderedDict[str, deque[SessionTurn]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def append_turn(self, session_id: str, turn: SessionTurn) -> None:
        async with self._lock:
            turns = self._sessions.get(session_id)
            if turns is None:
                turns = deque(maxlen=self._max_turns)
                self._sessions[session_id] = turns
                while len(self._sessions) > self._max_sessions:
                    self._sessions.popitem(last=False)  # bỏ phiên cũ nhất
            else:
                self._sessions.move_to_end(session_id)
            turns.append(turn)

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        async with self._lock:
            return list(self._sessions.get(session_id, ()))

    async def history_for_llm(self, session_id: str, n: int) -> list[dict]:
        """`n` lượt gần nhất dạng [{"role", "content"}], cũ -> mới."""
        if n <= 0:
            return []
        turns = await self.get_turns(session_id)
        messages: list[dict] = []
        for turn in turns[-n:]:
            messages.append({"role": "user", "content": turn.user_text})
            messages.append({"role": "assistant", "content": turn.reply})
        return messages

    def clear(self) -> None:
        self._sessions.clear()


store = SessionStore()
