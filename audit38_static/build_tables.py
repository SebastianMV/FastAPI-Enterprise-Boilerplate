"""Generate markdown tables from audit38 issues_full.json."""

from __future__ import annotations

import json
from pathlib import Path

out_dir = Path(__file__).parent
issues = json.loads((out_dir / "issues_full.json").read_text(encoding="utf-8"))

# ── Full table ──────────────────────────────────────────────
rows = []
for n, it in enumerate(issues, start=1):
    sev = it["severity"]
    rule = it["rule"]
    f = it["file"]
    line = it["line"]
    msg = it["message"].replace("|", "\\|")
    snip = it.get("snippet", "").replace("|", "\\|").replace("\n", " ").strip()[:120]
    rows.append(f"| {n} | {sev} | `{rule}` | `{f}` | {line} | {msg} | `{snip}` |")

header = (
    "# Audit N°38 - Tabla Completa de Issues\n\n"
    "| # | Sev | Rule | Archivo | Línea | Mensaje | Snippet |\n"
    "|---:|---:|---|---|---:|---|---|\n"
)
(out_dir / "AUDIT38_ISSUES_TABLE_FULL.md").write_text(
    header + "\n".join(rows) + "\n", encoding="utf-8"
)

# ── Summary table ────────────────────────────────────────────
summary = json.loads((out_dir / "issues_summary.json").read_text(encoding="utf-8"))
sev_rows = []
for sev, count in sorted(summary["by_severity"].items(), key=lambda x: -int(x[0])):
    sev_rows.append(f"| Sev {sev} | {count} |")

sev_table = (
    "# Audit N°38 - Resumen por Severidad\n\n"
    f"**Total issues: {summary['total_issues']}**\n\n"
    "| Severidad | Cantidad |\n"
    "|---|---|\n" + "\n".join(sev_rows) + "\n"
)
(out_dir / "AUDIT38_ISSUES_TABLE_SUMMARY.md").write_text(sev_table, encoding="utf-8")

# ── By-rule summary ──────────────────────────────────────────
rule_counts: dict[str, int] = {}
for it in issues:
    rule_counts[it["rule"]] = rule_counts.get(it["rule"], 0) + 1

rule_rows = []
for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1]):
    rule_rows.append(f"| `{rule}` | {count} |")

rule_table = (
    "# Audit N°38 - Resumen por Regla\n\n"
    "| Regla | Cantidad |\n"
    "|---|---|\n" + "\n".join(rule_rows) + "\n"
)
(out_dir / "AUDIT38_ISSUES_TABLE_BY_RULE.md").write_text(rule_table, encoding="utf-8")

print(f"Tables written. Total issues: {summary['total_issues']}")
for sev, cnt in sorted(summary["by_severity"].items(), key=lambda x: -int(x[0])):
    print(f"  Sev {sev}: {cnt}")
print("\nBy rule:")
for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1]):
    print(f"  {rule}: {count}")
