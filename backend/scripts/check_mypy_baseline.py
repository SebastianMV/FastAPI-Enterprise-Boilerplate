from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ERROR_LINE_PATTERN = re.compile(r"^(?P<path>[^:]+):\d+(?::\d+)?:\s+error:\s+.+$")


def normalize_path(raw_path: str) -> str:
    return raw_path.replace("\\", "/").strip()


def module_from_path(file_path: str) -> str:
    normalized = normalize_path(file_path)
    parts = normalized.split("/")
    if len(parts) >= 2 and parts[0] == "app":
        return f"app/{parts[1]}"
    if normalized.startswith("app"):
        return "app"
    return "other"


def parse_report(report_content: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in report_content.splitlines():
        match = ERROR_LINE_PATTERN.match(line)
        if match is None:
            continue
        module_name = module_from_path(match.group("path"))
        counts[module_name] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when MyPy error count grows vs versioned baseline"
    )
    parser.add_argument(
        "--baseline",
        default="mypy-baseline.json",
        help="Path to versioned baseline JSON",
    )
    parser.add_argument(
        "--report",
        default="mypy-report.txt",
        help="Path to current mypy report file",
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    report_path = Path(args.report)

    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline file not found: {baseline_path}")
    if not report_path.exists():
        raise FileNotFoundError(f"MyPy report file not found: {report_path}")

    baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_module_counts = {
        module_name: int(count)
        for module_name, count in baseline_data.get("module_errors", {}).items()
    }
    baseline_total = int(baseline_data.get("total_errors", 0))

    report_content = report_path.read_text(encoding="utf-8", errors="replace")
    current_counts = parse_report(report_content)
    current_total = int(sum(current_counts.values()))

    modules = sorted(set(baseline_module_counts) | set(current_counts.keys()))
    regressions: list[str] = []
    improvements: list[str] = []

    for module_name in modules:
        baseline_value = baseline_module_counts.get(module_name, 0)
        current_value = int(current_counts.get(module_name, 0))
        delta = current_value - baseline_value
        if delta > 0:
            regressions.append(
                f"{module_name}: {baseline_value} -> {current_value} (+{delta})"
            )
        elif delta < 0:
            improvements.append(
                f"{module_name}: {baseline_value} -> {current_value} ({delta})"
            )

    total_delta = current_total - baseline_total

    print("MyPy baseline check")
    print(f"- Baseline total: {baseline_total}")
    print(f"- Current total: {current_total}")
    print(f"- Delta: {total_delta:+d}")

    if improvements:
        print("Improvements by module:")
        for line in improvements:
            print(f"  - {line}")

    if regressions:
        print("Regressions by module:")
        for line in regressions:
            print(f"  - {line}")

    if regressions or total_delta > 0:
        print("❌ MyPy debt increased vs baseline. Failing check.")
        return 1

    print("✅ MyPy debt did not increase vs baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
