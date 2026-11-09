"""Import module không được kéo thư viện ML nặng (chỉ import trong thân hàm)."""

import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
HEAVY = ["torch", "transformers", "librosa", "numpy", "scipy", "sklearn"]


@pytest.mark.parametrize("module", ["emotion", "speech", "safety", "llm", "music"])
def test_import_is_light(module):
    code = (
        f"import sys, modules.{module}; "
        f"bad = [m for m in {HEAVY!r} if m in sys.modules]; "
        "print(','.join(bad)); sys.exit(1 if bad else 0)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0, f"modules/{module}.py import thư viện nặng: {proc.stdout.strip()}"
