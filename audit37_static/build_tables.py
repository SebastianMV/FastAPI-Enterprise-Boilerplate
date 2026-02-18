from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
issues = json.loads(
    (root / "audit37_static" / "issues_full.json").read_text(encoding="utf-8")
)

sev_counter = Counter(i["severity"] for i in issues)
rule_counter = Counter((i["severity"], i["rule"]) for i in issues)

full_lines = [
    "# Audit N°37 - Tabla Completa de Issues",
    "",
    "| # | Sev | Rule | Archivo | Línea | Mensaje |",
    "|---:|---:|---|---|---:|---|",
]
for idx, it in enumerate(issues, start=1):
    f = it["file"].replace("\\\\", "/")
    msg = it["message"].replace("|", "\\|")
    full_lines.append(
        f"| {idx} | {it['severity']} | {it['rule']} | {f} | {it['line']} | {msg} |"
    )

(root / "audit37_static" / "AUDIT37_ISSUES_TABLE_FULL.md").write_text(
    "\n".join(full_lines), encoding="utf-8"
)

sum_lines = [
    "# Audit N°37 - Tabla Resumen de Issues",
    "",
    "## Por severidad",
    "",
    "| Severidad | Cantidad |",
    "|---:|---:|",
]
for sev in sorted(sev_counter.keys(), reverse=True):
    sum_lines.append(f"| {sev} | {sev_counter[sev]} |")

sum_lines += [
    "",
    "## Por regla",
    "",
    "| Sev | Rule | Cantidad |",
    "|---:|---|---:|",
]
for (sev, rule), cnt in sorted(
    rule_counter.items(), key=lambda x: (-x[0][0], -x[1], x[0][1])
):
    sum_lines.append(f"| {sev} | {rule} | {cnt} |")

(root / "audit37_static" / "AUDIT37_ISSUES_TABLE_SUMMARY.md").write_text(
    "\n".join(sum_lines), encoding="utf-8"
)
print("ok")
