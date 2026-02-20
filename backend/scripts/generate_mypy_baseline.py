from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ERROR_LINE_PATTERN = re.compile(r"^(?P<path>[^:]+):\d+(?::\d+)?:\s+error:\s+.+$")


def normalize_path(raw_path: str) -> str:
    return raw_path.replace("\\", "/").strip()


def read_report_content(report_path: Path) -> str:
    raw = report_path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        content = raw.decode("utf-8", errors="replace")

    return content.replace("\x00", "")


def module_from_path(file_path: str) -> str:
    normalized = normalize_path(file_path)
    parts = normalized.split("/")
    if len(parts) >= 3 and parts[0] == "app":
        return f"app/{parts[1]}"
    if normalized.startswith("app"):
        return "app/root"
    return "other"


def parse_report(report_content: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in report_content.splitlines():
        cleaned_line = line.strip().lstrip("\ufeff\ufffd")
        match = ERROR_LINE_PATTERN.match(cleaned_line)
        if match is None:
            continue
        module_name = module_from_path(match.group("path"))
        counts[module_name] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate versioned MyPy baseline grouped by module"
    )
    parser.add_argument(
        "--report",
        default="mypy-report.txt",
        help="Path to mypy report file generated with mypy app",
    )
    parser.add_argument(
        "--output",
        default="mypy-baseline.json",
        help="Output baseline JSON path",
    )
    parser.add_argument(
        "--mypy-target",
        default="app",
        help="Mypy target used to build the report (metadata)",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    output_path = Path(args.output)

    if not report_path.exists():
        raise FileNotFoundError(f"MyPy report not found: {report_path}")

    report_content = read_report_content(report_path)
    module_counts = parse_report(report_content)
    module_counts_sorted = dict(sorted(module_counts.items(), key=lambda item: item[0]))

    baseline = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "mypy_target": args.mypy_target,
        "report_file": report_path.as_posix(),
        "total_errors": int(sum(module_counts.values())),
        "module_errors": module_counts_sorted,
    }

    output_path.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Baseline generated: {output_path}")
    print(f"Total errors: {baseline['total_errors']}")
    for module_name, count in sorted(
        module_counts.items(), key=lambda item: item[1], reverse=True
    ):
        print(f"- {module_name}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
