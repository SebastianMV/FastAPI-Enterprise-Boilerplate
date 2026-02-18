from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

issues: list[dict] = []


def add_issue(
    sev: int, rule: str, path: Path, line: int, message: str, snippet: str = ""
) -> None:
    issues.append(
        {
            "severity": sev,
            "rule": rule,
            "file": str(path.relative_to(ROOT)).replace("\\\\", "/"),
            "line": line,
            "message": message,
            "snippet": snippet.strip(),
        }
    )


# ---------- Backend endpoint checks ----------
endpoint_dir = ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
route_methods = {"get", "post", "put", "patch", "delete", "options", "head"}

for py in sorted(endpoint_dir.glob("*.py")):
    src = py.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    permission_aliases: set[str] = set()

    for n in tree.body:
        if isinstance(n, ast.Assign):
            if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                alias_name = n.targets[0].id
                value_text = ast.unparse(n.value)
                if "require_permission(" in value_text:
                    permission_aliases.add(alias_name)

    for node in tree.body:
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue

        is_route = False
        has_permission = False

        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                if dec.func.attr in route_methods:
                    is_route = True
                    for kw in dec.keywords or []:
                        if kw.arg == "dependencies" and isinstance(kw.value, ast.List):
                            for dep in kw.value.elts:
                                txt = ast.unparse(dep)
                                if "require_permission(" in txt:
                                    has_permission = True

        if not is_route:
            continue

        has_tenant = False
        has_authenticated_user = False
        all_args = [*node.args.args, *node.args.kwonlyargs]
        if node.args.vararg:
            all_args.append(node.args.vararg)
        if node.args.kwarg:
            all_args.append(node.args.kwarg)

        for arg in all_args:
            ann = ast.unparse(arg.annotation) if arg.annotation else ""
            if "CurrentTenantId" in ann or arg.arg == "tenant_id":
                has_tenant = True
                continue
            if (
                "CurrentUser" in ann
                or "CurrentActiveUser" in ann
                or "CurrentSuperuser" in ann
            ):
                has_authenticated_user = True
            if ann in permission_aliases or "require_permission(" in ann:
                has_permission = True
                has_authenticated_user = True

        arg_defaults_text = ""
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if default is not None:
                arg_defaults_text += " " + ast.unparse(default)
        if (
            "CurrentUser" in arg_defaults_text
            or "CurrentActiveUser" in arg_defaults_text
            or "CurrentSuperuser" in arg_defaults_text
        ):
            has_authenticated_user = True
        if "require_permission(" in arg_defaults_text:
            has_permission = True
            has_authenticated_user = True

        if has_authenticated_user and not has_tenant:
            add_issue(
                10,
                "backend.tenant.missing_current_tenant",
                py,
                node.lineno,
                "Endpoint route without CurrentTenantId/tenant_id parameter",
                lines[node.lineno - 1] if node.lineno <= len(lines) else "",
            )

        if has_authenticated_user and not has_permission:
            add_issue(
                8,
                "backend.authz.missing_require_permission",
                py,
                node.lineno,
                "Endpoint route without require_permission dependency",
                lines[node.lineno - 1] if node.lineno <= len(lines) else "",
            )


# ---------- Backend schema checks ----------
schema_dir = ROOT / "backend" / "app" / "api" / "v1" / "schemas"
allowed = {
    "NameStr",
    "ShortStr",
    "TextStr",
    "UrlStr",
    "TokenStr",
    "ScopeStr",
    "EmailStr",
}

for py in sorted(schema_dir.rglob("*.py")):
    if py.name in {"__init__.py", "common.py"}:
        continue
    src = py.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            ann_node = node.annotation
            ann = ast.unparse(ann_node)

            def _is_bare_str_type(expr: ast.expr) -> bool:
                if isinstance(expr, ast.Name):
                    return expr.id == "str"
                if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.BitOr):
                    left = _is_bare_str_type(expr.left)
                    right_is_none = (
                        isinstance(expr.right, ast.Constant)
                        and expr.right.value is None
                    )
                    right_is_none_name = (
                        isinstance(expr.right, ast.Name) and expr.right.id == "None"
                    )
                    right = _is_bare_str_type(expr.right)
                    left_is_none = (
                        isinstance(expr.left, ast.Constant) and expr.left.value is None
                    )
                    left_is_none_name = (
                        isinstance(expr.left, ast.Name) and expr.left.id == "None"
                    )
                    return (left and (right_is_none or right_is_none_name)) or (
                        right and (left_is_none or left_is_none_name)
                    )
                return False

            if _is_bare_str_type(ann_node) and not any(x in ann for x in allowed):
                add_issue(
                    7,
                    "backend.schemas.bare_str",
                    py,
                    node.lineno,
                    f"Schema field uses bare str annotation: {ann}",
                    lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                )


# ---------- Frontend checks ----------
frontend_dir = ROOT / "frontend" / "src"

console_re = re.compile(r"console\.(log|error|warn|debug)\(")
error_re = re.compile(r"error\.message|response\.data\.detail|response\.detail")
url_tpl_re = re.compile(r"`[^`]*\$\{([^}]+)\}[^`]*`")

for ts in sorted(frontend_dir.rglob("*.ts*")):
    if ts.name.endswith(".test.tsx") or ts.name.endswith(".test.ts"):
        continue
    text = ts.read_text(encoding="utf-8")
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        if console_re.search(line):
            window = "\\n".join(lines[max(0, i - 4) : i + 1])
            if "import.meta.env.DEV" not in window and "DEBUG" not in window:
                add_issue(
                    5,
                    "frontend.console.not_dev_guarded",
                    ts,
                    i,
                    "Console call appears outside DEV guard",
                    line,
                )

        if error_re.search(line):
            add_issue(
                6,
                "frontend.error.raw_message_exposure",
                ts,
                i,
                "Potential raw backend/frontend error message usage",
                line,
            )

        if "`" in line and "/api/" in line and "${" in line:
            m = url_tpl_re.search(line)
            if m and "encodeURIComponent(" not in line:
                add_issue(
                    6,
                    "frontend.url.unencoded_param",
                    ts,
                    i,
                    "Template URL interpolation without encodeURIComponent",
                    line,
                )

    # hardcoded visible strings in JSX attributes (heuristic)
    if ts.suffix.lower() == ".tsx":
        for i, line in enumerate(lines, start=1):
            if (
                re.search(r"(title|placeholder|aria-label|label|alt)=\"[A-Za-z]", line)
                and "t(" not in line
            ):
                add_issue(
                    4,
                    "frontend.i18n.hardcoded_attribute",
                    ts,
                    i,
                    "Possible hardcoded user-facing string (missing t())",
                    line,
                )


# ---------- Deduplicate ----------
unique = {}
for it in issues:
    key = (it["rule"], it["file"], it["line"], it["message"])
    if key not in unique:
        unique[key] = it

final_issues = sorted(
    unique.values(), key=lambda x: (-x["severity"], x["file"], x["line"])
)

out = ROOT / "audit36_static" / "issues_full.json"
out.write_text(json.dumps(final_issues, indent=2, ensure_ascii=False), encoding="utf-8")

# Aggregate counts
counts = {}
for it in final_issues:
    counts.setdefault(it["severity"], 0)
    counts[it["severity"]] += 1

summary = {
    "total_issues": len(final_issues),
    "by_severity": dict(sorted(counts.items(), reverse=True)),
}

(ROOT / "audit36_static" / "issues_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
)

print(json.dumps(summary, ensure_ascii=False))
