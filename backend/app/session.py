"""Bộ nhớ phiên trong RAM (mất khi restart; chạy uvicorn với --workers 1)."""

import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass

from app.constants import MAX_SESSION_TURNS, MAX_SESSIONS
from app.schemas import SessionTurn


@dataclass
class SessionState:
    """Bộ nhớ của một cuộc trò chuyện."""

    turns: deque[SessionTurn]
    total: int = 0  # số lượt đã thêm từ đầu phiên (chỉ số tuyệt đối)
    summary: str = ""
    summarized_count: int = 0  # số lượt đầu tiên đã nằm trong summary (chỉ số tuyệt đối)
    summarizing: bool = False  # đang có tác vụ tóm tắt chạy cho phiên này


@dataclass(frozen=True)
class MemorySnapshot:
    """Ảnh chụp bất biến của bộ nhớ phiên, dùng để dựng bối cảnh mà không giữ khoá."""

    turns: list[SessionTurn]
    total: int
    summary: str
    summarized_count: int

    @property
    def first_index(self) -> int:
        """Chỉ số tuyệt đối của lượt đầu trong `turns` (lượt cũ hơn đã bị deque xoá)."""
        return self.total - len(self.turns)

    @property
    def unsummarized(self) -> int:
        return self.total - self.summarized_count


class SessionStore:
    def __init__(self, max_turns: int = MAX_SESSION_TURNS, max_sessions: int = MAX_SESSIONS):
        self._max_turns = max_turns
        self._max_sessions = max_sessions
        self._sessions: OrderedDict[str, SessionState] = OrderedDict()
        self._lock = asyncio.Lock()

    async def append_turn(self, session_id: str, turn: SessionTurn) -> None:
        async with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                state = SessionState(turns=deque(maxlen=self._max_turns))
                self._sessions[session_id] = state
                while len(self._sessions) > self._max_sessions:
                    self._sessions.popitem(last=False)  # bỏ phiên cũ nhất (kèm bản tóm tắt)
            else:
                self._sessions.move_to_end(session_id)
            state.turns.append(turn)
            state.total += 1

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        async with self._lock:
            state = self._sessions.get(session_id)
            return list(state.turns) if state else []

    async def snapshot(self, session_id: str) -> MemorySnapshot:
        async with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                return MemorySnapshot(turns=[], total=0, summary="", summarized_count=0)
            return MemorySnapshot(
                turns=list(state.turns),
                total=state.total,
                summary=state.summary,
                summarized_count=state.summarized_count,
            )

    async def set_rating(self, session_id: str, turn_id: str, rating: str) -> bool:
        """Ghi đánh giá thích/không thích vào lượt; trả False nếu không tìm thấy lượt."""
        async with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                return False
            for turn in state.turns:
                if turn.turn_id == turn_id:
                    turn.rating = rating  # type: ignore[assignment]
                    return True
            return False

    async def begin_summary(self, session_id: str) -> SessionState | None:
        """Đánh dấu bắt đầu tóm tắt và trả trạng thái phiên.

        Trả None nếu phiên không có hoặc đã có tác vụ tóm tắt đang chạy.
        """
        async with self._lock:
            state = self._sessions.get(session_id)
            if state is None or state.summarizing:
                return None
            state.summarizing = True
            return state

    async def finish_summary(
        self,
        session_id: str,
        state: SessionState,
        summary: str | None = None,
        summarized_count: int | None = None,
    ) -> bool:
        """Kết thúc tác vụ tóm tắt; nếu có `summary` và số lượt mới thì ghi kết quả.

        Trả False (và không ghi gì) khi phiên đã bị xoá hoặc bị thay bằng phiên khác.
        """
        async with self._lock:
            if self._sessions.get(session_id) is not state:
                return False
            state.summarizing = False
            if summary is not None and summarized_count is not None:
                state.summary = summary
                state.summarized_count = summarized_count
            return True

    async def delete(self, session_id: str) -> None:
        """Xoá hẳn phiên (lượt, tóm tắt, trạng thái tóm tắt); không có phiên thì không làm gì.

        Tác vụ tóm tắt đang chạy cho phiên này sẽ bị bỏ kết quả: `finish_summary` so danh tính
        trạng thái nên không tạo lại phiên đã xoá, cũng không ghi vào phiên mới cùng id.
        """
        async with self._lock:
            self._sessions.pop(session_id, None)

    def clear(self) -> None:
        self._sessions.clear()


store = SessionStore()
