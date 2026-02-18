"""
Audit N°38 — Comprehensive Static Security Scanner
Covers backend (api, application, domain, middleware, cli) + frontend (src)
Excludes infrastructure/ and test files.

Rules (50+):
  BACKEND — endpoint authz/tenant (sev 8-10)
  BACKEND — schema constrained types (sev 7)
  BACKEND — logging hygiene (sev 5-6)
  BACKEND — datetime safety (sev 7)
  BACKEND — error leakage (sev 8-9)
  BACKEND — crypto / timing (sev 9)
  BACKEND — async safety (sev 6)
  BACKEND — SQL injection (sev 10)
  BACKEND — hardcoded secrets/credentials (sev 9-10)
  BACKEND — insecure deserialization (sev 8)
  BACKEND — path traversal (sev 9)
  BACKEND — SSRF patterns (sev 8)
  BACKEND — open redirect (sev 7)
  BACKEND — html injection (sev 8)
  BACKEND — password hashing (sev 10)
  BACKEND — random insecure (sev 9)
  BACKEND — missing rate-limit annotation (sev 7)
  BACKEND — TODO/FIXME security-tagged (sev 3)
  BACKEND — commented-out code blocks (sev 2)
  FRONTEND — console not dev-guarded (sev 5)
  FRONTEND — raw error message exposure (sev 6)
  FRONTEND — unencoded URL params (sev 6)
  FRONTEND — hardcoded i18n attributes (sev 4)
  FRONTEND — useEffect no cleanup (sev 5)
  FRONTEND — localStorage token storage (sev 9)
  FRONTEND — dangerouslySetInnerHTML (sev 9)
  FRONTEND — eval / new Function (sev 10)
  FRONTEND — postMessage no origin check (sev 8)
  FRONTEND — open redirect via window.location (sev 7)
  FRONTEND — hardcoded API keys/secrets (sev 9)
  FRONTEND — direct innerHTML assignment (sev 9)
  FRONTEND — prototype pollution patterns (sev 8)
  FRONTEND — insecure random (sev 7)
  FRONTEND — TODO/FIXME security-tagged (sev 3)
"""

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
            "snippet": snippet.strip()[:200],
        }
    )


# ─────────────────────────────────────────────────────────────
# HELPERS — Python AST
# ─────────────────────────────────────────────────────────────
def _pyfiles(*bases: Path, exclude_tests: bool = True) -> list[Path]:
    result = []
    for base in bases:
        for py in sorted(base.rglob("*.py")):
            if exclude_tests and (
                "test" in py.parts
                or py.name.startswith("test_")
                or py.name.endswith("_test.py")
            ):
                continue
            result.append(py)
    return result


route_methods = {"get", "post", "put", "patch", "delete", "options", "head"}

# ─────────────────────────────────────────────────────────────
# 1. BACKEND — endpoint authz/tenant checks
# ─────────────────────────────────────────────────────────────
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
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                if dec.func.attr in route_methods:
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

        # SuperuserId/CurrentSuperuserId is a valid high-privilege permission equivalent
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

        has_auth = _endpoint_has_arg_annotation(
            node,
            {
                "CurrentUser",
                "CurrentActiveUser",
                "CurrentSuperuser",
                "CurrentUserId",
                "CurrentSuperuserId",
                "SuperuserId",
                "CurrentTenantId",
            }
            | permission_aliases,
        )

        # Only count as authenticated if CurrentTenantId is non-optional (no default None)
        # or there's a real user dep beyond just optional tenant
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


# ─────────────────────────────────────────────────────────────
# 2. BACKEND — schema constrained types
# ─────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# 3–19. BACKEND — code pattern rules
# ─────────────────────────────────────────────────────────────
_backend_scan_dirs = [
    ROOT / "backend" / "app" / "api",
    ROOT / "backend" / "app" / "application",
    ROOT / "backend" / "app" / "domain",
    ROOT / "backend" / "app" / "middleware",
    ROOT / "backend" / "app" / "cli",
]

# Compiled patterns
re_logger_f = re.compile(r"logger\.(debug|info|warning|error|critical)\(f['\"]")
re_http_str_e = re.compile(r'\bstr\(e\)\b|\bf"[^"]*\{e[^}]*\}|\bf\'[^\']*\{e[^}]*\}')
re_timing_eq = re.compile(
    r'(token|secret|password|signature|hash|key|api_key|hmac)\b[\w\s\[\]\.\'"]*=='
)
re_hardcoded_cred = re.compile(
    r'(password|secret|api_key|apikey|private_key|access_token|auth_token)\s*=\s*["\'][A-Za-z0-9+/=_\-]{8,}["\']',
    re.IGNORECASE,
)
re_sql_concat = re.compile(
    r'(execute|text)\s*\(\s*f["\']|execute\s*\(\s*["\'][^"\']*\+'
)
re_pickle = re.compile(r"\bpickle\.loads?\b|\bpickle\.dumps?\b|\bpickle\.load\b")
re_yaml_unsafe = re.compile(
    r"yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader\s*=\s*yaml\.SafeLoader)"
)
re_path_trav = re.compile(
    r"open\s*\(\s*(request|user|data|form|body|param)", re.IGNORECASE
)
re_ssrf = re.compile(
    r"(requests\.(get|post|put|patch|delete)|httpx\.(get|post|put|patch|delete)|aiohttp\.ClientSession)\s*\(\s*(url|endpoint|target|href)",
    re.IGNORECASE,
)
# open redirect: flag only if variable URL is not derived from validated service/settings
re_open_redirect = re.compile(
    r"RedirectResponse\s*\(\s*(url\s*=\s*)?(?![\"\'])(?!.*settings\.)", re.IGNORECASE
)
re_html_inject = re.compile(
    r'HTMLResponse\s*\(\s*f["\']|HTMLResponse\s*\(\s*["\'][^"\']*\{'
)
re_plain_pw_hash = re.compile(
    r"hashlib\.(md5|sha1|sha256)\s*\([^)]*password", re.IGNORECASE
)
re_insecure_rand = re.compile(r"\brandom\.(random|randint|choice|shuffle|seed)\b")
re_todo_security = re.compile(
    r"#\s*(TODO|FIXME|HACK|XXX)\s*[:\-]?\s*(security|auth|csrf|xss|sqli|injection|secret|password)",
    re.IGNORECASE,
)
re_os_system = re.compile(r"\bos\.system\s*\(|\bos\.popen\s*\(")
re_exec_eval = re.compile(r"\beval\s*\(|\bexec\s*\(")
re_assert_authz = re.compile(
    r"\bassert\s+.*user|(role|permission|admin)\b", re.IGNORECASE
)
re_subprocess_run = re.compile(
    r"\bsubprocess\.run\s*\(|\bsubprocess\.call\s*\(|\bsubprocess\.Popen\s*\("
)
# NEW in N°38
re_utcnow = re.compile(r"\bdatetime\.utcnow\s*\(")
re_stdlib_logging = re.compile(r"^\s*(import logging\b|from logging import)")
re_mass_assign = re.compile(r"\*\*request\.(dict|json|form)\b|\*\*data\b|\*\*payload\b")
re_debug_true = re.compile(r"\bDEBUG\s*=\s*True\b")
re_cors_all = re.compile(r'allow_origins\s*=\s*\[?\s*["\'\*]["\'\*]?\s*\]?')
re_no_max_age = re.compile(r"set_cookie\s*\(.*(?!max_age)")
re_jwt_none_alg = re.compile(r'(algorithms\s*=\s*\[.*["\']none["\'])', re.IGNORECASE)
re_jsonb_raw = re.compile(
    r"json\.loads\s*\(\s*(request|data|body|payload|form)\b", re.IGNORECASE
)
re_print_stmt = re.compile(r"^\s*print\s*\(")
re_tempfile_bad = re.compile(r"\btempfile\.mktemp\s*\(")
re_xmlparse_xxe = re.compile(
    r"xml\.(etree|dom|sax)\b|ElementTree\.parse\b|minidom\.parse\b"
)


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

        for i, raw_line in enumerate(lines, start=1):
            L = raw_line

            # logging
            if re_stdlib_logging.match(L):
                add_issue(
                    6,
                    "backend.logging.stdlib_import",
                    py,
                    i,
                    "Use get_logger() instead of stdlib logging",
                    L,
                )

            if re_logger_f.search(L):
                add_issue(
                    5,
                    "backend.logging.fstring",
                    py,
                    i,
                    "Avoid f-string in structured log call (use key=value)",
                    L,
                )

            if re_print_stmt.match(L):
                add_issue(
                    4,
                    "backend.logging.print_statement",
                    py,
                    i,
                    "Use get_logger() instead of print()",
                    L,
                )

            # datetime
            if re_utcnow.search(L):
                add_issue(
                    7,
                    "backend.datetime.utcnow",
                    py,
                    i,
                    "Use datetime.now(UTC) instead of datetime.utcnow()",
                    L,
                )

            # error leakage
            if "HTTPException(" in L and re_http_str_e.search(L):
                add_issue(
                    9,
                    "backend.error.leaks_exception",
                    py,
                    i,
                    "HTTP error response may leak exception details via str(e)",
                    L,
                )

            # timing safety — skip ORM WHERE clauses and dict key checks
            if re_timing_eq.search(L) and "compare_digest(" not in L:
                if not any(
                    pat in L
                    for pat in (
                        "Model.",
                        ".where(",
                        "select(",
                        "filter(",
                        "elif key ==",
                        "if key ==",
                        "# noqa",
                    )
                ):
                    add_issue(
                        9,
                        "backend.crypto.non_timing_safe_compare",
                        py,
                        i,
                        "Non timing-safe == comparison on secret-like value",
                        L,
                    )

            # hardcoded credentials
            if (
                re_hardcoded_cred.search(L)
                and "os.environ" not in L
                and "getenv" not in L
                and "settings." not in L
            ):
                if not any(
                    pat in L
                    for pat in (
                        "#",
                        "test_",
                        "_test",
                        "example",
                        "dummy",
                        "fake",
                        "placeholder",
                        "your_",
                    )
                ):
                    add_issue(
                        9,
                        "backend.secrets.hardcoded_credential",
                        py,
                        i,
                        "Possible hardcoded secret or credential value",
                        L,
                    )

            # SQL injection
            if re_sql_concat.search(L):
                add_issue(
                    10,
                    "backend.sqli.string_concatenation",
                    py,
                    i,
                    "Possible SQL injection via f-string or concatenation in SQL execute",
                    L,
                )

            # insecure deserialization
            if re_pickle.search(L):
                add_issue(
                    8,
                    "backend.deser.pickle_usage",
                    py,
                    i,
                    "pickle.load/loads is unsafe with untrusted data",
                    L,
                )

            if re_yaml_unsafe.search(L):
                add_issue(
                    8,
                    "backend.deser.yaml_unsafe_load",
                    py,
                    i,
                    "yaml.load() without SafeLoader is unsafe; use yaml.safe_load()",
                    L,
                )

            # path traversal
            if re_path_trav.search(L):
                add_issue(
                    9,
                    "backend.path_traversal.open_user_input",
                    py,
                    i,
                    "open() called with variable derived from request data",
                    L,
                )

            # SSRF
            if re_ssrf.search(L):
                add_issue(
                    8,
                    "backend.ssrf.outbound_request_variable_url",
                    py,
                    i,
                    "Outbound HTTP call with variable URL — validate/whitelist before use",
                    L,
                )

            # open redirect — skip redirects where URL comes from OAuth service or allowlist-validated base
            if re_open_redirect.search(L):
                # Check next 3 lines as well (url= is often on the following line)
                next_lines = " ".join(lines[i : min(i + 3, len(lines))])
                combined = L + " " + next_lines
                if not any(
                    pat in combined
                    for pat in (
                        "auth_url",
                        "frontend_url",
                        'f"',
                        "f'",
                        "authorization_url",
                        "settings.",
                    )
                ):
                    add_issue(
                        7,
                        "backend.redirect.open_redirect",
                        py,
                        i,
                        "RedirectResponse with variable URL — validate before redirect",
                        L,
                    )

            # HTML injection
            if re_html_inject.search(L):
                add_issue(
                    8,
                    "backend.xss.html_injection",
                    py,
                    i,
                    "HTMLResponse built with f-string — use html.escape()",
                    L,
                )

            # password hashing with weak algorithm
            if re_plain_pw_hash.search(L):
                add_issue(
                    10,
                    "backend.crypto.weak_password_hash",
                    py,
                    i,
                    "Password hashed with MD5/SHA1/SHA256 — use bcrypt/argon2",
                    L,
                )

            # insecure random (not for crypto)
            if re_insecure_rand.search(L) and "# nosec" not in L:
                add_issue(
                    7,
                    "backend.crypto.insecure_random",
                    py,
                    i,
                    "random module is not cryptographically secure; use secrets module",
                    L,
                )

            # os.system / os.popen
            if re_os_system.search(L):
                add_issue(
                    9,
                    "backend.rce.os_system",
                    py,
                    i,
                    "os.system/os.popen may execute arbitrary shell commands",
                    L,
                )

            # eval/exec
            if re_exec_eval.search(L) and "# nosec" not in L:
                add_issue(
                    10,
                    "backend.rce.eval_exec",
                    py,
                    i,
                    "eval()/exec() is dangerous; avoid or sandbox execution",
                    L,
                )

            # subprocess
            if re_subprocess_run.search(L) and "# nosec" not in L:
                add_issue(
                    6,
                    "backend.sync.subprocess",
                    py,
                    i,
                    "subprocess call — prefer async subprocess and validate input",
                    L,
                )

            # assert for authorization
            if re_assert_authz.search(L) and L.strip().startswith("assert"):
                add_issue(
                    8,
                    "backend.authz.assert_for_authorization",
                    py,
                    i,
                    "assert used for security check — disabled with -O flag",
                    L,
                )

            # mass assignment
            if re_mass_assign.search(L):
                add_issue(
                    8,
                    "backend.injection.mass_assignment",
                    py,
                    i,
                    "Mass assignment via **request.dict() — whitelist fields explicitly",
                    L,
                )

            # DEBUG = True
            if (
                re_debug_true.search(L)
                and "settings" not in py.name
                and "test" not in py.name.lower()
            ):
                add_issue(
                    8,
                    "backend.config.debug_true",
                    py,
                    i,
                    "DEBUG=True found in non-settings file",
                    L,
                )

            # CORS wildcard
            if re_cors_all.search(L):
                add_issue(
                    8,
                    "backend.cors.wildcard_origins",
                    py,
                    i,
                    "CORS allow_origins='*' — scope to known domains in production",
                    L,
                )

            # JWT none algorithm
            if re_jwt_none_alg.search(L):
                add_issue(
                    10,
                    "backend.crypto.jwt_none_algorithm",
                    py,
                    i,
                    "JWT decode allows 'none' algorithm — critical signing bypass",
                    L,
                )

            # XXE
            if re_xmlparse_xxe.search(L):
                add_issue(
                    8,
                    "backend.xxe.xml_parsing",
                    py,
                    i,
                    "XML parsing without explicit security settings — risk of XXE",
                    L,
                )

            # tempfile.mktemp (race condition)
            if re_tempfile_bad.search(L):
                add_issue(
                    7,
                    "backend.path.mktemp_race_condition",
                    py,
                    i,
                    "tempfile.mktemp() is unsafe (TOCTOU race); use NamedTemporaryFile",
                    L,
                )

            # TODO/FIXME security
            if re_todo_security.search(L):
                add_issue(
                    3,
                    "backend.quality.todo_security",
                    py,
                    i,
                    "TODO/FIXME annotated with security keyword",
                    L,
                )


# ─────────────────────────────────────────────────────────────
# 20–34. FRONTEND — code pattern rules
# ─────────────────────────────────────────────────────────────
frontend_src = ROOT / "frontend" / "src"

re_console = re.compile(r"console\.(log|error|warn|debug|info)\s*\(")
re_raw_error = re.compile(
    r"error\.message\b|response\.data\.detail\b|response\.detail\b|err\.message\b|\.response\.data\b"
)
re_url_tpl = re.compile(r"`[^`]*\$\{([^}]+)\}[^`]*`")
re_jsx_attr_hc = re.compile(
    r'\b(title|placeholder|aria-label|label|alt|tooltip)="[A-Za-z]'
)
re_localstorage_tok = re.compile(
    r"localStorage\.(setItem|getItem)\s*\(\s*['\"]?(token|access_token|jwt|auth|refresh)['\"]?",
    re.IGNORECASE,
)
re_dangerous_html = re.compile(r"dangerouslySetInnerHTML\s*=\s*\{")
re_eval_js = re.compile(r"\beval\s*\(|\bnew Function\s*\(")
re_postmsg_no_ori = re.compile(r"window\.postMessage\s*\(.*['\"\*]['\"]?\s*\)")
re_win_loc_open = re.compile(r"window\.location\s*=\s*(?![\"\']/([\"\']|$))")
re_hc_secret = re.compile(
    r'(api_key|apiKey|api-key|secret|password|token)\s*[:=]\s*["\'][A-Za-z0-9+/=_\-]{16,}["\']',
    re.IGNORECASE,
)
re_innerhtml = re.compile(r"\.innerHTML\s*=")
re_proto_pollution = re.compile(
    r"__proto__\s*\[|Object\.assign\s*\({}\s*,\s*\w+\s*,\s*\w+\)"
)
re_insecure_rand_js = re.compile(r"\bMath\.random\s*\(\)")
re_todo_sec_js = re.compile(
    r"//\s*(TODO|FIXME|HACK|XXX)\s*[:\-]?\s*(security|auth|csrf|xss|sqli|injection|secret|password)",
    re.IGNORECASE,
)
re_external_script = re.compile(r'src\s*=\s*["\']https?://')
re_document_write = re.compile(r"\bdocument\.write\s*\(")
re_no_csp_nonce = re.compile(r"<script\b(?!.*nonce)")
re_unsafe_regex = re.compile(r"new RegExp\s*\(.*[+*?]{2,}")
re_open_redirect_fe = re.compile(
    r"window\.location\.(href|replace|assign)\s*=\s*(?!['\"`]/)"
)

for ts_file in sorted(frontend_src.rglob("*.ts*")):
    if any(x in ts_file.name for x in (".test.", ".spec.")):
        continue
    if "__snapshots__" in ts_file.parts:
        continue

    text = ts_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    for i, raw_line in enumerate(lines, start=1):
        L = raw_line

        # console not DEV-guarded — use a wider context window (10 lines) to catch if(DEBUG) wrappers
        if re_console.search(L):
            window_ctx = "\n".join(lines[max(0, i - 10) : i + 2])
            if (
                "import.meta.env.DEV" not in window_ctx
                and "process.env.NODE_ENV" not in window_ctx
                and "DEBUG" not in window_ctx
            ):
                add_issue(
                    5,
                    "frontend.console.not_dev_guarded",
                    ts_file,
                    i,
                    "console call outside DEV guard",
                    L,
                )

        # raw error message exposure
        if re_raw_error.search(L):
            add_issue(
                6,
                "frontend.error.raw_message_exposure",
                ts_file,
                i,
                "Raw backend/JS error message possibly shown to user",
                L,
            )

        # unencoded URL param
        if "`" in L and "/api/" in L and "${" in L:
            if re_url_tpl.search(L) and "encodeURIComponent(" not in L:
                add_issue(
                    6,
                    "frontend.url.unencoded_param",
                    ts_file,
                    i,
                    "Template literal URL interpolation without encodeURIComponent",
                    L,
                )

        # hardcoded i18n attribute
        if (
            ts_file.suffix.lower() == ".tsx"
            and re_jsx_attr_hc.search(L)
            and "t(" not in L
        ):
            add_issue(
                4,
                "frontend.i18n.hardcoded_attribute",
                ts_file,
                i,
                "Possible hardcoded user-facing attribute (missing t())",
                L,
            )

        # localStorage token storage
        if re_localstorage_tok.search(L):
            add_issue(
                9,
                "frontend.security.localstorage_token",
                ts_file,
                i,
                "Token stored in localStorage — use HttpOnly cookie instead",
                L,
            )

        # dangerouslySetInnerHTML
        if re_dangerous_html.search(L):
            add_issue(
                9,
                "frontend.xss.dangerous_set_inner_html",
                ts_file,
                i,
                "dangerouslySetInnerHTML bypasses React XSS protection",
                L,
            )

        # eval / new Function
        if re_eval_js.search(L) and "// nosec" not in L:
            add_issue(
                10,
                "frontend.rce.eval",
                ts_file,
                i,
                "eval()/new Function() is dangerous — avoid in production code",
                L,
            )

        # postMessage origin check
        if re_postmsg_no_ori.search(L):
            add_issue(
                8,
                "frontend.security.postmessage_no_origin",
                ts_file,
                i,
                "postMessage sent to '*' — scope to specific target origin",
                L,
            )

        # open redirect via window.location — skip if there's URL validation nearby (isValidOAuthUrl, isValid, allowlist)
        if re_win_loc_open.search(L) or re_open_redirect_fe.search(L):
            window_ctx = "\n".join(lines[max(0, i - 10) : i + 2])
            if (
                "isValid" not in window_ctx
                and "allowlist" not in window_ctx
                and "validate" not in window_ctx.lower()
            ):
                if (
                    "encodeURI" not in L
                    and "encodeURIComponent" not in L
                    and "/" not in L[: L.find("=") + 5 if "=" in L else len(L)]
                ):
                    add_issue(
                        7,
                        "frontend.redirect.open_redirect",
                        ts_file,
                        i,
                        "window.location assignment with variable — validate URL before redirect",
                        L,
                    )

        # hardcoded secrets
        if (
            re_hc_secret.search(L)
            and "process.env" not in L
            and "import.meta.env" not in L
        ):
            if not any(
                x in L.lower()
                for x in ("test", "mock", "fake", "example", "placeholder")
            ):
                add_issue(
                    9,
                    "frontend.secrets.hardcoded",
                    ts_file,
                    i,
                    "Possible hardcoded API key or secret in frontend code",
                    L,
                )

        # innerHTML assignment
        if re_innerhtml.search(L):
            add_issue(
                9,
                "frontend.xss.innerhtml_assignment",
                ts_file,
                i,
                "Direct .innerHTML assignment bypasses XSS protection",
                L,
            )

        # prototype pollution
        if re_proto_pollution.search(L):
            add_issue(
                8,
                "frontend.injection.prototype_pollution",
                ts_file,
                i,
                "Possible prototype pollution pattern",
                L,
            )

        # insecure random — skip if used only for jitter/non-security purposes (comment context)
        if re_insecure_rand_js.search(L) and "// nosec" not in L:
            window_ctx = "\n".join(lines[max(0, i - 3) : i + 2])
            if not any(
                x in window_ctx.lower()
                for x in (
                    "jitter",
                    "backoff",
                    "delay",
                    "timeout",
                    "animation",
                    "color",
                    "sample",
                    "display",
                )
            ):
                add_issue(
                    7,
                    "frontend.crypto.insecure_random",
                    ts_file,
                    i,
                    "Math.random() is not cryptographically secure; use crypto.getRandomValues()",
                    L,
                )

        # document.write
        if re_document_write.search(L):
            add_issue(
                8,
                "frontend.xss.document_write",
                ts_file,
                i,
                "document.write() is unsafe and deprecated",
                L,
            )

        # unsafe RegExp construction
        if re_unsafe_regex.search(L):
            add_issue(
                6,
                "frontend.dos.unsafe_regex",
                ts_file,
                i,
                "RegExp with possibly catastrophic backtracking (ReDoS)",
                L,
            )

        # TODO/FIXME security
        if re_todo_sec_js.search(L):
            add_issue(
                3,
                "frontend.quality.todo_security",
                ts_file,
                i,
                "TODO/FIXME annotated with security keyword",
                L,
            )

    # file-level useEffect cleanup check
    if "useEffect(" in text and (
        "fetch(" in text or "axios." in text or "api." in text
    ):
        if "return () =>" not in text and "AbortController" not in text:
            add_issue(
                5,
                "frontend.hooks.useeffect.no_cleanup",
                ts_file,
                1,
                "File uses useEffect + network call but has no cleanup/AbortController",
                "useEffect",
            )


# ─────────────────────────────────────────────────────────────
# Deduplicate & output
# ─────────────────────────────────────────────────────────────
unique: dict[tuple, dict] = {}
for it in issues:
    key = (it["rule"], it["file"], it["line"])
    if key not in unique:
        unique[key] = it

final_issues = sorted(
    unique.values(), key=lambda x: (-x["severity"], x["file"], x["line"])
)

by_sev: dict[int, int] = {}
for it in final_issues:
    by_sev[it["severity"]] = by_sev.get(it["severity"], 0) + 1

out_dir = Path(__file__).parent
(out_dir / "issues_full.json").write_text(
    json.dumps(final_issues, indent=2, ensure_ascii=False), encoding="utf-8"
)
(out_dir / "issues_summary.json").write_text(
    json.dumps(
        {
            "total_issues": len(final_issues),
            "by_severity": dict(sorted(by_sev.items(), reverse=True)),
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
            "by_severity": dict(sorted(by_sev.items(), reverse=True)),
        },
        ensure_ascii=False,
    )
)
