"""Xuất backend/openapi.json cho frontend sinh kiểu TypeScript.

Chạy: python -m app.tools.export_openapi   (từ thư mục backend)
"""

import json
import sys
from pathlib import Path

from app.main import app

OUTPUT = Path(__file__).resolve().parents[2] / "openapi.json"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Đã ghi {OUTPUT}")


if __name__ == "__main__":
    main()
