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
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "line": line,
            "message": message,
            "snippet": snippet.strip(),
        }
    )


# =========================
# Backend: API endpoints
# =========================
endpoint_dir = ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
route_methods = {"get", "post", "put", "patch", "delete", "options", "head"}

for py in sorted(endpoint_dir.glob("*.py")):
    src = py.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)

    permission_aliases: set[str] = set()
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            alias_name = node.targets[0].id
            if "require_permission(" in ast.unparse(node.value):
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
                                dep_txt = ast.unparse(dep)
                                if "require_permission(" in dep_txt:
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
            if (
                "CurrentUser" in ann
                or "CurrentActiveUser" in ann
                or "CurrentSuperuser" in ann
            ):
                has_authenticated_user = True
            if ann in permission_aliases or "require_permission(" in ann:
                has_permission = True
                has_authenticated_user = True

        defaults_text = ""
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if default is not None:
                defaults_text += " " + ast.unparse(default)

        if (
            "CurrentUser" in defaults_text
            or "CurrentActiveUser" in defaults_text
            or "CurrentSuperuser" in defaults_text
        ):
            has_authenticated_user = True
        if "require_permission(" in defaults_text:
            has_permission = True
            has_authenticated_user = True

        if has_authenticated_user and not has_tenant:
            add_issue(
                10,
                "backend.tenant.missing_current_tenant",
                py,
                node.lineno,
                "Authenticated endpoint without CurrentTenantId/tenant_id parameter",
                lines[node.lineno - 1] if node.lineno <= len(lines) else "",
            )

        if has_authenticated_user and not has_permission:
            add_issue(
                8,
                "backend.authz.missing_require_permission",
                py,
                node.lineno,
                "Authenticated endpoint without require_permission dependency",
                lines[node.lineno - 1] if node.lineno <= len(lines) else "",
            )


# =========================
# Backend: code patterns (excluding infrastructure)
# =========================
backend_scan_dirs = [
    ROOT / "backend" / "app" / "api",
    ROOT / "backend" / "app" / "application",
    ROOT / "backend" / "app" / "domain",
    ROOT / "backend" / "app" / "middleware",
    ROOT / "backend" / "app" / "cli",
]

re_logger_f = re.compile(r"logger\.(debug|info|warning|error|critical)\(f\"")
re_http_str_e = re.compile(r"str\(e\)|\{e\}")
re_timing_eq = re.compile(r"(token|secret|password|signature|hash)[\w\s\]\[\.'\"]*==")

for base in backend_scan_dirs:
    for py in sorted(base.rglob("*.py")):
        src = py.read_text(encoding="utf-8")
        lines = src.splitlines()

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            if stripped.startswith("import logging") or stripped.startswith(
                "from logging import"
            ):
                add_issue(
                    6,
                    "backend.logging.stdlib_import",
                    py,
                    i,
                    "Use centralized get_logger instead of stdlib logging",
                    line,
                )

            if re_logger_f.search(line):
                add_issue(
                    5,
                    "backend.logging.fstring",
                    py,
                    i,
                    "Avoid f-strings in structured logging",
                    line,
                )

            if "datetime.utcnow(" in line:
                add_issue(
                    7,
                    "backend.datetime.utcnow",
                    py,
                    i,
                    "Use datetime.now(UTC) instead of datetime.utcnow()",
                    line,
                )

            if "HTTPException(" in line and re_http_str_e.search(line):
                add_issue(
                    9,
                    "backend.error.leaks_exception",
                    py,
                    i,
                    "HTTP error response may leak exception details",
                    line,
                )

            if "subprocess.run(" in line:
                add_issue(
                    6,
                    "backend.sync.subprocess_run",
                    py,
                    i,
                    "Use async subprocess APIs in async backend code",
                    line,
                )

            if (
                re_timing_eq.search(line)
                and "compare_digest(" not in line
                and "Model." not in line
                and ".where(" not in line
                and "select(" not in line
            ):
                add_issue(
                    9,
                    "backend.crypto.non_timing_safe_compare",
                    py,
                    i,
                    "Potential non timing-safe comparison for secret-like values",
                    line,
                )


# =========================
# Backend: schemas constrained types
# =========================
schema_dir = ROOT / "backend" / "app" / "api" / "v1" / "schemas"
allowed = {
    "NameStr",
    "ShortStr",
    "TextStr",
    "LargeTextStr",
    "UrlStr",
    "TokenStr",
    "ScopeStr",
    "LongNameStr",
    "RoleNameStr",
    "DescriptionStr",
    "PasswordStr",
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
                    left_bare = _is_bare_str_type(expr.left)
                    right_bare = _is_bare_str_type(expr.right)
                    left_none = (
                        isinstance(expr.left, ast.Constant) and expr.left.value is None
                    ) or (isinstance(expr.left, ast.Name) and expr.left.id == "None")
                    right_none = (
                        isinstance(expr.right, ast.Constant)
                        and expr.right.value is None
                    ) or (isinstance(expr.right, ast.Name) and expr.right.id == "None")
                    return (left_bare and right_none) or (right_bare and left_none)
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


# =========================
# Frontend checks
# =========================
frontend_dir = ROOT / "frontend" / "src"

console_re = re.compile(r"console\.(log|error|warn|debug)\(")
error_re = re.compile(r"error\.message|response\.data\.detail|response\.detail")
url_tpl_re = re.compile(r"`[^`]*\$\{([^}]+)\}[^`]*`")
jsx_literal_attr_re = re.compile(r"(title|placeholder|aria-label|label|alt)=\"[A-Za-z]")

for ts in sorted(frontend_dir.rglob("*.ts*")):
    # skip tests to avoid noise
    if (
        ".test." in ts.name
        or ts.name.endswith(".spec.ts")
        or ts.name.endswith(".spec.tsx")
    ):
        continue

    text = ts.read_text(encoding="utf-8")
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        if console_re.search(line):
            window = "\n".join(lines[max(0, i - 5) : i + 1])
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

        if (
            ts.suffix.lower() == ".tsx"
            and jsx_literal_attr_re.search(line)
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

    # heuristic: useEffect with network call but no cleanup
    if "useEffect(" in text and ("fetch(" in text or "axios." in text):
        if "return () =>" not in text and "AbortController" not in text:
            add_issue(
                5,
                "frontend.hooks.useeffect.no_cleanup",
                ts,
                1,
                "Possible useEffect without cleanup/AbortController for async work",
                "useEffect",
            )


# =========================
# Dedupe & output
# =========================
unique = {}
for it in issues:
    key = (it["rule"], it["file"], it["line"], it["message"])
    if key not in unique:
        unique[key] = it

final_issues = sorted(
    unique.values(), key=lambda x: (-x["severity"], x["file"], x["line"])
)

counts = {}
for it in final_issues:
    counts[it["severity"]] = counts.get(it["severity"], 0) + 1

(root := ROOT / "audit37_static")
(root / "issues_full.json").write_text(
    json.dumps(final_issues, indent=2, ensure_ascii=False), encoding="utf-8"
)
(root / "issues_summary.json").write_text(
    json.dumps(
        {
            "total_issues": len(final_issues),
            "by_severity": dict(sorted(counts.items(), reverse=True)),
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "total_issues": len(final_issues),
            "by_severity": dict(sorted(counts.items(), reverse=True)),
        },
        ensure_ascii=False,
    )
)
