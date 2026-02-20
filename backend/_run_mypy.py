"""Re-run mypy and update report."""
from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
mypy_exe = ROOT / ".venv" / "Scripts" / "mypy.exe"

result = subprocess.run(
    [str(mypy_exe), "app", "--show-error-codes", "--no-color-output"],
    capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
)

report = result.stdout + result.stderr
(ROOT / "mypy-report.txt").write_text(report, encoding="utf-8")

error_lines = [l for l in report.splitlines() if ": error:" in l]
print(f"Total errors: {len(error_lines)}")

codes: Counter[str] = Counter()
for line in error_lines:
    if line.endswith("]"):
        code = line.rsplit("[", 1)[-1].rstrip("]")
        codes[code] += 1

for code, count in codes.most_common():
    print(f"  [{code}]: {count}")
