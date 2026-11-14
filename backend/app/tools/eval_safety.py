"""Đánh giá bộ lọc an toàn trên bộ câu thử có nhãn.

Chạy trong `backend/`:
    python -m app.tools.eval_safety
    python -m app.tools.eval_safety --cases đường/dẫn/khác.csv --list-errors

In số câu, số bỏ sót, số báo nhầm theo từng nhóm, cùng recall, precision và F1 tổng.
Luôn thoát với mã 0 (đây là công cụ đo, không phải cổng chặn).
"""

import argparse
import csv
import sys
import time
from collections import OrderedDict
from pathlib import Path

DEFAULT_CASES = Path(__file__).resolve().parents[2] / "tests" / "data" / "safety_cases.csv"
CATEGORIES = ["direct", "indirect", "no_accent", "negation", "idiom", "normal"]


def load_cases(path: Path = DEFAULT_CASES) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return [
            {"text": row["text"], "risk": row["risk"].strip() == "1", "category": row["category"]}
            for row in csv.DictReader(f)
        ]


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def _f1(precision: float | None, recall: float | None) -> float | None:
    if not precision or not recall:
        return 0.0 if precision is not None and recall is not None else None
    return 2 * precision * recall / (precision + recall)


def evaluate(cases: list[dict], check=None) -> dict:
    """Chạy `check_safety` trên từng câu; trả số liệu theo nhóm, tổng và danh sách lỗi."""
    if check is None:
        from modules.safety import check_safety as check

    groups: OrderedDict[str, dict] = OrderedDict()
    errors: list[dict] = []
    check("khởi động")  # khởi động trước (biên dịch luật) để thời gian đo không tính lần đầu
    started = time.perf_counter()
    for case in cases:
        predicted = bool(check(case["text"])["risk"])
        g = groups.setdefault(
            case["category"], {"n": 0, "positive": 0, "tp": 0, "fn": 0, "fp": 0, "tn": 0}
        )
        g["n"] += 1
        g["positive"] += case["risk"]
        if case["risk"] and predicted:
            g["tp"] += 1
        elif case["risk"]:
            g["fn"] += 1
            errors.append({**case, "kind": "bỏ sót"})
        elif predicted:
            g["fp"] += 1
            errors.append({**case, "kind": "báo nhầm"})
        else:
            g["tn"] += 1
    elapsed_ms = (time.perf_counter() - started) * 1000

    total = {
        k: sum(g[k] for g in groups.values()) for k in ("n", "positive", "tp", "fn", "fp", "tn")
    }
    recall = _ratio(total["tp"], total["tp"] + total["fn"])
    precision = _ratio(total["tp"], total["tp"] + total["fp"])
    ordered = OrderedDict((c, groups[c]) for c in CATEGORIES if c in groups)
    ordered.update((c, g) for c, g in groups.items() if c not in ordered)
    return {
        "groups": ordered,
        "total": total,
        "recall": recall,
        "precision": precision,
        "f1": _f1(precision, recall),
        "ms_per_case": elapsed_ms / len(cases) if cases else 0.0,
        "errors": errors,
    }


def _fmt(value: float | None) -> str:
    return "  -  " if value is None else f"{value:.3f}"


def format_report(result: dict) -> str:
    lines = [
        f"{'Nhóm':<10} {'Số câu':>7} {'Nguy hiểm':>10} {'Bỏ sót':>7} {'Báo nhầm':>9} "
        f"{'Recall':>7} {'Precision':>10}",
        "-" * 66,
    ]
    for name, g in [*result["groups"].items(), ("TỔNG", result["total"])]:
        recall = _ratio(g["tp"], g["tp"] + g["fn"])
        precision = _ratio(g["tp"], g["tp"] + g["fp"])
        lines.append(
            f"{name:<10} {g['n']:>7} {g['positive']:>10} {g['fn']:>7} {g['fp']:>9} "
            f"{_fmt(recall):>7} {_fmt(precision):>10}"
        )
    lines += [
        "",
        f"Recall tổng: {_fmt(result['recall'])}   Precision tổng: {_fmt(result['precision'])}   "
        f"F1 tổng: {_fmt(result['f1'])}",
        f"Thời gian trung bình: {result['ms_per_case']:.3f} ms/câu",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đánh giá bộ lọc an toàn trên bộ câu có nhãn.")
    parser.add_argument(
        "--cases", type=Path, default=DEFAULT_CASES, help="File CSV text,risk,category"
    )
    parser.add_argument(
        "--list-errors", action="store_true", help="Liệt kê từng câu bỏ sót/báo nhầm"
    )
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = evaluate(load_cases(args.cases))
    print(format_report(result))
    if args.list_errors and result["errors"]:
        print("\nCâu sai:")
        for e in result["errors"]:
            print(f"  [{e['kind']}] ({e['category']}) {e['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
