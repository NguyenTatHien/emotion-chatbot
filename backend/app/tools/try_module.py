"""Thử nhanh một module: python -m app.tools.try_module <module> <đầu vào>

Ví dụ:
    python -m app.tools.try_module emotion "hôm nay vui ghê"
    python -m app.tools.try_module music Sadness --arousal low --goal xoa_diu
"""

import argparse
import json
import sys

from app import registry
from app.constants import MODULE_NAMES


def run(module: str, value: str, arousal: str | None, goal: str | None) -> dict:
    mode = registry.mode_of(module)
    if module == "emotion":
        result = registry.get("emotion")(value)
    elif module == "safety":
        result = registry.get("safety")(value)
    elif module == "speech":
        result = {
            "transcript": registry.get("speech", "transcribe")(value),
            "prosody": registry.get("speech", "extract_prosody")(value),
        }
    elif module == "llm":
        emotion = registry.get("emotion")(value)
        result = registry.get("llm")(value, emotion, arousal, [], goal)
    elif module == "music":
        result = registry.get("music")(value, arousal, goal, 5)
    else:
        raise SystemExit(f"Module không hợp lệ: {module}")
    return {"module": module, "mode": mode, "result": result}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thử nhanh một module theo mode đang chọn.")
    parser.add_argument("module", choices=MODULE_NAMES)
    parser.add_argument(
        "input",
        help="Văn bản (emotion/safety/llm), đường dẫn WAV (speech) hoặc nhãn cảm xúc (music)",
    )
    parser.add_argument("--arousal", choices=["low", "medium", "high"], default=None)
    parser.add_argument("--goal", default=None)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = parser.parse_args(argv)

    try:
        output = run(args.module, args.input, args.arousal, args.goal)
    except NotImplementedError as exc:
        print(f"Chưa implement: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
