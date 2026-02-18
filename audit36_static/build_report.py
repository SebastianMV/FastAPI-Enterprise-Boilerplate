from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
issues = json.loads(
    (root / "audit36_static" / "issues_full.json").read_text(encoding="utf-8")
)

lines: list[str] = [
    "# Audit N°36 - Listado Único de Issues (Excluye Infraestructura)",
    "",
    f"Total issues: {len(issues)}",
    "",
]

cur = None
for it in issues:
    sev = it["severity"]
    if sev != cur:
        lines.append(f"## Severidad {sev}/10")
        cur = sev
    file = it["file"].replace("\\\\", "/")
    lines.append(f"- [{it['rule']}] {file}:{it['line']} — {it['message']}")

(root / "audit36_static" / "AUDIT36_ISSUES.md").write_text(
    "\n".join(lines), encoding="utf-8"
)
print(f"ok {len(issues)}")
