from __future__ import annotations

import json
from pathlib import Path

out_dir = Path(__file__).parent
issues = json.loads((out_dir / "issues_full.json").read_text(encoding="utf-8"))
summary = json.loads((out_dir / "issues_summary.json").read_text(encoding="utf-8"))

full_rows: list[str] = []
for idx, it in enumerate(issues, start=1):
    message = it["message"].replace("|", "\\|")
    snippet = it.get("snippet", "").replace("|", "\\|").replace("\n", " ")
    full_rows.append(
        f"| {idx} | {it['severity']} | `{it['rule']}` | `{it['file']}` | {it['line']} | {message} | `{snippet}` |"
    )

(out_dir / "AUDIT41_ISSUES_TABLE_FULL.md").write_text(
    "# Audit N°41 - Tabla Completa de Issues\n\n"
    "| # | Sev | Rule | Archivo | Línea | Mensaje | Snippet |\n"
    "|---:|---:|---|---|---:|---|---|\n" + "\n".join(full_rows) + "\n",
    encoding="utf-8",
)

sev_rows = [
    f"| Sev {sev} | {cnt} |"
    for sev, cnt in sorted(summary["by_severity"].items(), key=lambda x: -int(x[0]))
]

(out_dir / "AUDIT41_ISSUES_TABLE_SUMMARY.md").write_text(
    "# Audit N°41 - Resumen por Severidad\n\n"
    f"**Total issues: {summary['total_issues']}**\n\n"
    "| Severidad | Cantidad |\n"
    "|---|---|\n" + "\n".join(sev_rows) + "\n",
    encoding="utf-8",
)

rule_counts: dict[str, int] = {}
for it in issues:
    rule_counts[it["rule"]] = rule_counts.get(it["rule"], 0) + 1

rule_rows = [
    f"| `{rule}` | {cnt} |"
    for rule, cnt in sorted(rule_counts.items(), key=lambda x: -x[1])
]

(out_dir / "AUDIT41_ISSUES_TABLE_BY_RULE.md").write_text(
    "# Audit N°41 - Resumen por Regla\n\n"
    "| Regla | Cantidad |\n"
    "|---|---|\n" + "\n".join(rule_rows) + "\n",
    encoding="utf-8",
)

print(f"Tables written. Total issues: {summary['total_issues']}")
for sev, cnt in sorted(summary["by_severity"].items(), key=lambda x: -int(x[0])):
    print(f"  Sev {sev}: {cnt}")
