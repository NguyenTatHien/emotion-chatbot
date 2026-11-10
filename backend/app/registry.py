"""Registry chọn implementation của từng module theo mode: mock | local | remote.

Pipeline chỉ lấy hàm qua `registry.get(...)`, không import trực tiếp `modules/` hay `mocks/`.
"""

import importlib
from collections.abc import Callable

from app.config import get_settings
from app.constants import MODULE_NAMES

# Hàm mặc định của từng module và danh sách hàm hợp lệ.
DEFAULT_FUNCS = {
    "emotion": "predict_emotion",
    "speech": "transcribe",
    "safety": "check_safety",
    "llm": "generate_reply",
    "music": "recommend",
}
VALID_FUNCS = {
    "emotion": {"predict_emotion"},
    "speech": {"transcribe", "extract_prosody"},
    "safety": {"check_safety"},
    "llm": {"generate_reply"},
    "music": {"recommend"},
}

_overrides: dict[tuple[str, str], Callable] = {}


# Hàm remote có sẵn trong client model server (safety và music luôn chạy trong backend).
REMOTE_FUNCS = {"emotion", "speech", "llm"}


class RemoteNotConfigured(RuntimeError):
    """Module ở mode `remote` nhưng không có client tương ứng (safety, music)."""


def _resolve_func(name: str, func: str | None) -> str:
    if name not in MODULE_NAMES:
        raise KeyError(f"Module không tồn tại: {name}")
    func = func or DEFAULT_FUNCS[name]
    if func not in VALID_FUNCS[name]:
        raise KeyError(f"Module {name} không có hàm {func}")
    return func


def mode_of(name: str) -> str:
    return get_settings().module_mode(name)


def llm_backend_name() -> str:
    """Tên nguồn trả lời khi LLM đang chọn chạy thành công: mock | gemini | qwen."""
    mode = mode_of("llm")
    return mode if mode in ("mock", "gemini") else "qwen"


def get(name: str, func: str | None = None) -> Callable:
    """Trả callable của module `name` theo mode hiện hành (hoặc bản override trong test)."""
    func = _resolve_func(name, func)
    if (name, func) in _overrides:
        return _overrides[(name, func)]

    mode = mode_of(name)
    if mode == "gemini":  # chỉ LLM_MODE nhận giá trị này (đã kiểm ở config)
        from app import gemini

        return gemini.generate_reply
    if mode == "remote":
        if name not in REMOTE_FUNCS:
            raise RemoteNotConfigured(f"Module '{name}' không hỗ trợ mode remote")
        from app.clients import model_server

        return getattr(model_server, func)

    package = "mocks" if mode == "mock" else "modules"
    module = importlib.import_module(f"{package}.{name}")
    return getattr(module, func)


def override(name: str, fn: Callable, func: str | None = None) -> None:
    """Thay implementation (dùng trong test)."""
    _overrides[(name, _resolve_func(name, func))] = fn


def reset_overrides() -> None:
    _overrides.clear()
