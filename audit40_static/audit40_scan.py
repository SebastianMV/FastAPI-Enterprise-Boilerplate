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
            "snippet": snippet.strip()[:220],
        }
    )


# ============================================================
# 1) BACKEND/FRONTEND scan (reuse baseline from audit38)
# ============================================================
route_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
endpoint_dir = ROOT / "backend" / "app" / "api" / "v1" / "endpoints"


def _collect_permission_aliases(tree: ast.Module) -> set[str]:
    aliases: set[str] = set()
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            if "require_permission(" in ast.unparse(node.value):
                aliases.add(node.targets[0].id)
    return aliases


def _endpoint_has_arg_annotation(
    fn: ast.AsyncFunctionDef | ast.FunctionDef, keywords: set[str]
) -> bool:
    all_args = [*fn.args.args, *fn.args.kwonlyargs]
    for arg in all_args:
        ann = ast.unparse(arg.annotation) if arg.annotation else ""
        if any(kw in ann for kw in keywords):
            return True
    for default in [*fn.args.defaults, *fn.args.kw_defaults]:
        if default is not None:
            dtext = ast.unparse(default)
            if any(kw in dtext for kw in keywords):
                return True
    return False


for py in sorted(endpoint_dir.glob("*.py")):
    if py.name == "__init__.py":
        continue
    src = py.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    permission_aliases = _collect_permission_aliases(tree)

    for node in tree.body:
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue

        is_route = False
        dec_has_permission = False

        for dec in node.decorator_list:
            if (
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr in route_methods
            ):
                is_route = True
                for kw in dec.keywords or []:
                    if kw.arg == "dependencies" and isinstance(kw.value, ast.List):
                        for dep in kw.value.elts:
                            if "require_permission(" in ast.unparse(dep):
                                dec_has_permission = True

        if not is_route:
            continue

        has_tenant = _endpoint_has_arg_annotation(
            node, {"CurrentTenantId", "CurrentSuperuserTenantId"}
        ) or any(
            arg.arg == "tenant_id" for arg in [*node.args.args, *node.args.kwonlyargs]
        )
        has_superuser_dep = _endpoint_has_arg_annotation(
            node, {"SuperuserId", "CurrentSuperuserId"}
        )
        has_permission = (
            dec_has_permission
            or has_superuser_dep
            or _endpoint_has_arg_annotation(
                node, permission_aliases | {"require_permission("}
            )
        )
        has_real_auth = (
            _endpoint_has_arg_annotation(
                node,
                {
                    "CurrentUser",
                    "CurrentActiveUser",
                    "CurrentSuperuser",
                    "CurrentUserId",
                    "CurrentSuperuserId",
                    "SuperuserId",
                }
                | permission_aliases,
            )
            or dec_has_permission
        )

        if has_real_auth and not has_tenant:
            add_issue(
                10,
                "backend.tenant.missing_current_tenant",
                py,
                node.lineno,
                f"Authenticated endpoint `{node.name}` lacks CurrentTenantId/tenant_id",
                lines[node.lineno - 1],
            )

        if has_real_auth and not has_permission:
            add_issue(
                8,
                "backend.authz.missing_require_permission",
                py,
                node.lineno,
                f"Authenticated endpoint `{node.name}` lacks require_permission dependency",
                lines[node.lineno - 1],
            )


schema_dir = ROOT / "backend" / "app" / "api" / "v1" / "schemas"
_ALLOWED_STR_TYPES = {
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


def _is_bare_str(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "str"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        l_bare = _is_bare_str(node.left)
        r_bare = _is_bare_str(node.right)
        l_none = isinstance(node.left, ast.Name) and node.left.id == "None"
        r_none = isinstance(node.right, ast.Name) and node.right.id == "None"
        return (l_bare and r_none) or (r_bare and l_none)
    return False


for py in sorted(schema_dir.rglob("*.py")):
    if py.name in {"__init__.py", "common.py"}:
        continue
    src = py.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            ann = ast.unparse(node.annotation)
            if _is_bare_str(node.annotation) and not any(
                a in ann for a in _ALLOWED_STR_TYPES
            ):
                add_issue(
                    7,
                    "backend.schemas.bare_str",
                    py,
                    node.lineno,
                    f"Schema field `{node.target.id}` uses bare str annotation",
                    lines[node.lineno - 1],
                )


_backend_scan_dirs = [
    ROOT / "backend" / "app" / "api",
    ROOT / "backend" / "app" / "application",
    ROOT / "backend" / "app" / "domain",
    ROOT / "backend" / "app" / "middleware",
    ROOT / "backend" / "app" / "cli",
]

re_stdlib_logging = re.compile(r"^\s*(import logging\b|from logging import)")
re_logger_f = re.compile(r"logger\.(debug|info|warning|error|critical)\(f['\"]")
re_http_str_e = re.compile(r'\bstr\(e\)\b|\bf"[^"]*\{e[^}]*\}|\bf\'[^\']*\{e[^}]*\}')
re_timing_eq = re.compile(
    r"(token|secret|password|signature|hash|key|api_key|hmac)\b[\w\s\[\]\.\'\"]*=="
)
re_utcnow = re.compile(r"\bdatetime\.utcnow\s*\(")
re_subprocess = re.compile(r"\bsubprocess\.(run|call|Popen)\s*\(")

for base in _backend_scan_dirs:
    for py in sorted(base.rglob("*.py")):
        if (
            "test" in py.parts
            or py.name.startswith("test_")
            or py.name.endswith("_test.py")
        ):
            continue
        src = py.read_text(encoding="utf-8")
        lines = src.splitlines()
        for i, line in enumerate(lines, start=1):
            if re_stdlib_logging.match(line):
                add_issue(
                    6,
                    "backend.logging.stdlib_import",
                    py,
                    i,
                    "Use get_logger() instead of stdlib logging",
                    line,
                )
            if re_logger_f.search(line):
                add_issue(
                    5,
                    "backend.logging.fstring",
                    py,
                    i,
                    "Avoid f-string in structured log",
                    line,
                )
            if re_utcnow.search(line):
                add_issue(
                    7, "backend.datetime.utcnow", py, i, "Use datetime.now(UTC)", line
                )
            if "HTTPException(" in line and re_http_str_e.search(line):
                add_issue(
                    9,
                    "backend.error.leaks_exception",
                    py,
                    i,
                    "Potential exception details leak",
                    line,
                )
            if re_subprocess.search(line):
                add_issue(
                    6,
                    "backend.sync.subprocess",
                    py,
                    i,
                    "Prefer async subprocess in async backend",
                    line,
                )
            if re_timing_eq.search(line) and "compare_digest(" not in line:
                if not any(
                    p in line
                    for p in (
                        "Model.",
                        ".where(",
                        "select(",
                        "filter(",
                        "if key ==",
                        "elif key ==",
                    )
                ):
                    add_issue(
                        9,
                        "backend.crypto.non_timing_safe_compare",
                        py,
                        i,
                        "Potential non timing-safe comparison",
                        line,
                    )


# Frontend
frontend_src = ROOT / "frontend" / "src"
re_console = re.compile(r"console\.(log|error|warn|debug|info)\s*\(")
re_raw_error = re.compile(
    r"error\.message\b|response\.data\.detail\b|response\.detail\b|err\.message\b"
)
re_url_tpl = re.compile(r"`[^`]*\$\{([^}]+)\}[^`]*`")
re_eval_js = re.compile(r"\beval\s*\(|\bnew Function\s*\(")

for ts_file in sorted(frontend_src.rglob("*.ts*")):
    if any(x in ts_file.name for x in (".test.", ".spec.")):
        continue
    text = ts_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        if re_console.search(line):
            ctx = "\n".join(lines[max(0, i - 10) : i + 2])
            if (
                "import.meta.env.DEV" not in ctx
                and "DEBUG" not in ctx
                and "NODE_ENV" not in ctx
            ):
                add_issue(
                    5,
                    "frontend.console.not_dev_guarded",
                    ts_file,
                    i,
                    "Console outside DEV guard",
                    line,
                )
        if re_raw_error.search(line):
            add_issue(
                6,
                "frontend.error.raw_message_exposure",
                ts_file,
                i,
                "Potential raw error exposure",
                line,
            )
        if (
            "`" in line
            and "/api/" in line
            and "${" in line
            and re_url_tpl.search(line)
            and "encodeURIComponent(" not in line
        ):
            add_issue(
                6,
                "frontend.url.unencoded_param",
                ts_file,
                i,
                "API URL interpolation without encodeURIComponent",
                line,
            )
        if re_eval_js.search(line):
            add_issue(
                10, "frontend.rce.eval", ts_file, i, "eval/new Function usage", line
            )


# ============================================================
# 2) INFRASTRUCTURE scan (NEW in audit39)
# ============================================================
infra_files: list[Path] = []
infra_files.extend(sorted(ROOT.glob("docker-compose*.yml")))
infra_files.extend(sorted((ROOT / ".github" / "workflows").glob("*.yml")))
for p in [
    ROOT / "backend" / "Dockerfile",
    ROOT / "backend" / "Dockerfile.prod",
    ROOT / "frontend" / "Dockerfile",
    ROOT / "frontend" / "Dockerfile.dev",
    ROOT / "frontend" / "nginx.conf",
    ROOT / "frontend" / "nginx.dev.conf",
]:
    if p.exists():
        infra_files.append(p)

# compose + docker hardening patterns
re_image = re.compile(r"^\s*image:\s*([^\s#]+)")
re_unpinned_image = re.compile(r"^\s*image:\s*[^\s#]+:(latest|\d+(?:\.\d+)?)(\s|$)")
re_secrets_default = re.compile(r"\$\{([^}:]+):-([^}]+)\}")
re_secrets_required = re.compile(r"\$\{[^}:]+:\?[^}]+\}")
re_no_new_priv = re.compile(r"no-new-privileges:true")
re_cap_drop_all = re.compile(r"cap_drop:\s*\n\s*-\s*ALL", re.IGNORECASE)
re_user_root = re.compile(r"^\s*USER\s+root\b", re.IGNORECASE)
re_from_latest = re.compile(r"^\s*FROM\s+[^\s:]+(?::latest)?\s*$", re.IGNORECASE)
re_action_tag = re.compile(r"^\s*uses:\s*[^@\s]+@v\d", re.IGNORECASE)
re_action_sha = re.compile(r"^\s*uses:\s*[^@\s]+@[a-f0-9]{40}\b", re.IGNORECASE)
re_allow_all_cors = re.compile(
    r"add_header\s+Access-Control-Allow-Origin\s+['\"]?\*", re.IGNORECASE
)

for file_path in infra_files:
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Global scans by line
    for i, line in enumerate(lines, start=1):
        if re_unpinned_image.search(line):
            add_issue(
                7,
                "infra.docker.image_unpinned",
                file_path,
                i,
                "Docker image tag should be pinned to minor/patch, not latest/major",
                line,
            )

        m_default = re_secrets_default.search(line)
        if m_default:
            var_name = (m_default.group(1) or "").upper()
            is_sensitive_var = any(
                k in var_name for k in ("SECRET", "KEY", "TOKEN", "PASSWORD", "URL")
            )
            is_strict_compose = file_path.name in {
                "docker-compose.staging.yml",
                "docker-compose.prod.yml",
            }
            if is_strict_compose and is_sensitive_var:
                add_issue(
                    9,
                    "infra.secrets.unsafe_default",
                    file_path,
                    i,
                    "Use ${VAR:?must be set} instead of ${VAR:-default} in non-dev configs",
                    line,
                )

        if file_path.parts[-3:] == (".github", "workflows", file_path.name):
            if re_action_tag.search(line) and not re_action_sha.search(line):
                add_issue(
                    8,
                    "infra.github_action.unpinned",
                    file_path,
                    i,
                    "GitHub Action should be pinned by commit SHA",
                    line,
                )

        if file_path.name.startswith("nginx") and re_allow_all_cors.search(line):
            add_issue(
                8,
                "infra.nginx.cors_wildcard",
                file_path,
                i,
                "Nginx CORS wildcard origin detected",
                line,
            )

        if file_path.name.startswith("Dockerfile"):
            if re_user_root.search(line):
                add_issue(
                    8,
                    "infra.dockerfile.user_root",
                    file_path,
                    i,
                    "Container runs as root user",
                    line,
                )
            if re_from_latest.search(line):
                add_issue(
                    7,
                    "infra.dockerfile.from_unpinned",
                    file_path,
                    i,
                    "Base image should be pinned explicitly",
                    line,
                )

    # Compose block-level checks for security_opt/cap_drop
    if file_path.name.startswith("docker-compose"):
        has_no_new_priv = "no-new-privileges:true" in text
        has_cap_drop = "cap_drop:" in text and "- ALL" in text

        # only enforce for staging/prod per project rules
        if file_path.name in {"docker-compose.staging.yml", "docker-compose.prod.yml"}:
            if not has_no_new_priv:
                add_issue(
                    9,
                    "infra.compose.missing_no_new_privileges",
                    file_path,
                    1,
                    "Compose file missing security_opt no-new-privileges:true",
                    "security_opt",
                )
            if not has_cap_drop:
                add_issue(
                    9,
                    "infra.compose.missing_cap_drop_all",
                    file_path,
                    1,
                    "Compose file missing cap_drop: [ALL]",
                    "cap_drop",
                )

            # If any secret interpolation exists but no required-form interpolation appears, flag weak posture
            if "${" in text and not re_secrets_required.search(text):
                add_issue(
                    8,
                    "infra.compose.secrets_not_fail_fast",
                    file_path,
                    1,
                    "Compose appears to use env vars without fail-fast :? guards",
                    "${VAR}",
                )


# ============================================================
# 3) dedupe + output
# ============================================================
unique: dict[tuple, dict] = {}
for it in issues:
    key = (it["rule"], it["file"], it["line"], it["message"])
    if key not in unique:
        unique[key] = it

final_issues = sorted(
    unique.values(), key=lambda x: (-x["severity"], x["file"], x["line"])
)

by_severity: dict[int, int] = {}
for it in final_issues:
    by_severity[it["severity"]] = by_severity.get(it["severity"], 0) + 1

out_dir = Path(__file__).parent
(out_dir / "issues_full.json").write_text(
    json.dumps(final_issues, indent=2, ensure_ascii=False), encoding="utf-8"
)
(out_dir / "issues_summary.json").write_text(
    json.dumps(
        {
            "total_issues": len(final_issues),
            "by_severity": dict(sorted(by_severity.items(), reverse=True)),
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
            "by_severity": dict(sorted(by_severity.items(), reverse=True)),
        },
        ensure_ascii=False,
    )
)
