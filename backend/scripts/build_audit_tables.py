"""Generate Markdown report tables from audit_scan.py output.

Usage (run from repo root or any directory):
    python backend/scripts/build_audit_tables.py [audit_label]

    audit_label: label used in output filenames (default: "LATEST")

Output files are written next to this script:
    issues_table_full.md
    issues_table_summary.md
    issues_table_by_rule.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

out_dir = Path(__file__).parent
label = sys.argv[1] if len(sys.argv) > 1 else "LATEST"

issues_path = out_dir / "issues_full.json"
summary_path = out_dir / "issues_summary.json"

if not issues_path.exists() or not summary_path.exists():
    print("Run audit_scan.py first to generate issues_full.json and issues_summary.json")
    sys.exit(1)

issues = json.loads(issues_path.read_text(encoding="utf-8"))
summary = json.loads(summary_path.read_text(encoding="utf-8"))

# --- Full table ---
full_rows: list[str] = []
for idx, it in enumerate(issues, start=1):
    message = it["message"].replace("|", "\\|")
    snippet = it.get("snippet", "").replace("|", "\\|").replace("\n", " ")
    full_rows.append(
        f"| {idx} | {it['severity']} | `{it['rule']}` | `{it['file']}` | {it['line']} | {message} | `{snippet}` |"
    )

(out_dir / "issues_table_full.md").write_text(
    f"# Audit {label} — Full Issues Table\n\n"
    "| # | Sev | Rule | File | Line | Message | Snippet |\n"
    "|---:|---:|---|---|---:|---|---|\n" + "\n".join(full_rows) + "\n",
    encoding="utf-8",
)

# --- Summary table ---
sev_rows = [
    f"| Sev {sev} | {cnt} |"
    for sev, cnt in sorted(summary["by_severity"].items(), key=lambda x: -int(x[0]))
]

(out_dir / "issues_table_summary.md").write_text(
    f"# Audit {label} — Summary by Severity\n\n"
    f"**Total issues: {summary['total_issues']}**\n\n"
    "| Severity | Count |\n"
    "|---|---|\n" + "\n".join(sev_rows) + "\n",
    encoding="utf-8",
)

# --- By-rule table ---
rule_counts: dict[str, int] = {}
for it in issues:
    rule_counts[it["rule"]] = rule_counts.get(it["rule"], 0) + 1

rule_rows = [
    f"| `{rule}` | {cnt} |"
    for rule, cnt in sorted(rule_counts.items(), key=lambda x: -x[1])
]

(out_dir / "issues_table_by_rule.md").write_text(
    f"# Audit {label} — Summary by Rule\n\n"
    "| Rule | Count |\n"
    "|---|---|\n" + "\n".join(rule_rows) + "\n",
    encoding="utf-8",
)

print(f"Tables written to {out_dir}. Total issues: {summary['total_issues']}")
