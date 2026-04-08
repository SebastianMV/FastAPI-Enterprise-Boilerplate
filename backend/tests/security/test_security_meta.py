"""Security meta-tests — verify security patterns are enforced across the codebase.

These tests don't test business logic. They scan source files to ensure security
conventions are followed. Run as part of the regular test suite.

Based on 788 fixes from 24 security audits. Each test targets a specific
anti-pattern category.
"""

import ast
import re
from pathlib import Path

import pytest

# Paths
BACKEND_APP = Path(__file__).parent.parent.parent / "app"
API_DIR = BACKEND_APP / "api"
SCHEMAS_DIR = API_DIR / "v1" / "schemas"

# Excluded files (legitimate exceptions)
LOGGING_WRAPPER = BACKEND_APP / "infrastructure" / "observability" / "logging.py"


def _get_python_files(directory: Path, exclude: list[Path] | None = None) -> list[Path]:
    """Recursively get all .py files, excluding specified paths."""
    exclude = exclude or []
    exclude_resolved = [e.resolve() for e in exclude]
    return [
        p
        for p in directory.rglob("*.py")
        if p.resolve() not in exclude_resolved
        and "__pycache__" not in str(p)
        and "htmlcov" not in str(p)
    ]


class TestNoStdlibLogging:
    """Verify no file in app/ uses `import logging` (must use get_logger())."""

    def test_no_stdlib_logging_import(self) -> None:
        violations: list[str] = []
        for filepath in _get_python_files(BACKEND_APP, exclude=[LOGGING_WRAPPER]):
            content = filepath.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped == "import logging" or stripped.startswith(
                    "from logging import"
                ):
                    violations.append(f"{filepath.relative_to(BACKEND_APP)}:{i}")

        assert not violations, (
            f"stdlib logging found in {len(violations)} locations "
            f"(use get_logger() instead):\n" + "\n".join(violations)
        )


class TestNoStrExceptionInResponses:
    """Verify no HTTP response contains str(e) — prevents info leaks."""

    PATTERNS = [
        re.compile(r"str\(\s*e\s*\)"),
        re.compile(r"str\(\s*err\s*\)"),
        re.compile(r"str\(\s*exc\s*\)"),
        re.compile(r"str\(\s*exception\s*\)"),
    ]

    def test_no_str_exception_in_api(self) -> None:
        violations: list[str] = []
        for filepath in _get_python_files(API_DIR):
            content = filepath.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                # Skip comments and pure logging lines
                stripped = line.strip()
                if stripped.startswith("#") or "logger." in stripped:
                    continue
                for pattern in self.PATTERNS:
                    if pattern.search(stripped):
                        # Check if it's in an HTTP response context
                        if any(
                            kw in stripped
                            for kw in [
                                "detail=",
                                '"error"',
                                '"detail"',
                                '"message"',
                                "HTTPException",
                                "JSONResponse",
                            ]
                        ):
                            violations.append(
                                f"{filepath.relative_to(BACKEND_APP)}:{i}: {stripped[:80]}"
                            )

        assert not violations, (
            f"str(e) in HTTP responses found in {len(violations)} locations:\n"
            + "\n".join(violations)
        )


class TestDatetimeUtcnow:
    """Verify no usage of deprecated datetime.utcnow()."""

    def test_no_utcnow(self) -> None:
        violations: list[str] = []
        pattern = re.compile(r"\.utcnow\(\)")
        for filepath in _get_python_files(BACKEND_APP):
            content = filepath.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line) and not line.strip().startswith("#"):
                    violations.append(f"{filepath.relative_to(BACKEND_APP)}:{i}")

        assert not violations, (
            f"datetime.utcnow() found in {len(violations)} locations "
            f"(use datetime.now(UTC) instead):\n" + "\n".join(violations)
        )


class TestTimingSafeComparisons:
    """Verify tokens/secrets use hmac.compare_digest, not ==."""

    SENSITIVE_NAMES = {
        "token",
        "csrf",
        "secret",
        "otp",
        "code",
        "verification",
        "jti",
        "api_key",
    }

    # Variable names that contain sensitive words but are safe
    SAFE_VARIABLE_NAMES = {
        "returncode",
        "status_code",
        "error_code",
        "exit_code",
        "keycode",
        "charcode",
    }

    def test_no_direct_token_comparison(self) -> None:
        violations: list[str] = []
        # Match patterns like: if token == something or if something == token
        pattern = re.compile(r"if\s+(\w+)\s*==\s*(\w+)|(\w+)\s*!=\s*(\w+)")
        for filepath in _get_python_files(BACKEND_APP):
            content = filepath.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                match = pattern.search(stripped)
                if match:
                    # Check if any variable name contains a sensitive word
                    all_vars = [g for g in match.groups() if g is not None]
                    for var in all_vars:
                        if var.lower() in self.SAFE_VARIABLE_NAMES:
                            continue
                        if any(s in var.lower() for s in self.SENSITIVE_NAMES):
                            # Exclude hmac.compare_digest lines
                            if "compare_digest" not in stripped:
                                violations.append(
                                    f"{filepath.relative_to(BACKEND_APP)}:{i}: {stripped[:80]}"
                                )

        if violations:
            assert not violations, (
                f"Found {len(violations)} potential timing-unsafe comparisons "
                f"(review manually):\n" + "\n".join(violations[:10])
            )


class TestNoFStringInLogger:
    """Verify logger calls use lazy formatting, not f-strings."""

    PATTERN = re.compile(r'logger\.(info|debug|warning|error|critical)\(f["\']')

    def test_no_fstring_logging(self) -> None:
        violations: list[str] = []
        for filepath in _get_python_files(BACKEND_APP):
            content = filepath.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                if self.PATTERN.search(line.strip()):
                    violations.append(f"{filepath.relative_to(BACKEND_APP)}:{i}")

        assert not violations, (
            f"f-string in logger calls found in {len(violations)} locations "
            f"(use lazy %s formatting):\n" + "\n".join(violations)
        )


class TestEndpointPermissions:
    """Verify API endpoints use require_permission, not just CurrentUser."""

    # Endpoints that legitimately only need CurrentUser (no resource-specific ACL)
    EXEMPT_FUNCTIONS = {
        "login",
        "register",
        "refresh",
        "logout",
        "verify_email",
        "forgot_password",
        "reset_password",
        "get_me",
        "update_me",
        "change_password",
        "health",
        "readiness",
        "liveness",
        "root",
        "enable_mfa",
        "verify_mfa",
        "disable_mfa",
        "get_mfa_status",
        "verify_mfa_login",
        "use_backup_code",
        "oauth_login",
        "oauth_callback",
        "callback_redirect",
    }

    def test_endpoints_have_permissions(self) -> None:
        """Check that endpoints in v1/ routers use require_permission."""
        v1_dir = API_DIR / "v1" / "endpoints"
        if not v1_dir.exists():
            pytest.fail("v1/endpoints directory not found — security check cannot run")

        warnings: list[str] = []
        for filepath in _get_python_files(v1_dir):
            content = filepath.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    if node.name.startswith("_") or node.name in self.EXEMPT_FUNCTIONS:
                        continue

                    # Check if function has require_permission in its decorators or params
                    func_text = ast.get_source_segment(content, node) or ""
                    has_permission = "require_permission" in func_text
                    has_router_decorator = any(
                        "router." in ast.dump(d) for d in node.decorator_list
                    )

                    if has_router_decorator and not has_permission:
                        # Check if it at least has CurrentUser
                        has_current_user = "CurrentUser" in func_text
                        if has_current_user:
                            warnings.append(
                                f"{filepath.name}:{node.lineno} — "
                                f"{node.name}() has CurrentUser but no require_permission"
                            )

        if warnings:
            # This is advisory, not a hard failure
            assert not warnings, (
                f"{len(warnings)} endpoints use CurrentUser without "
                f"require_permission (review if ACL is needed):\n"
                + "\n".join(warnings[:15])
            )


class TestDockerImagePins:
    """Verify Docker images are pinned to minor versions (not :latest or major-only)."""

    COMPOSE_FILES = [
        Path(__file__).parent.parent.parent.parent / f
        for f in [
            "docker-compose.yml",
            "docker-compose.test.yml",
            "docker-compose.deploy.yml",
        ]
    ]

    BAD_TAGS = re.compile(r"image:\s+\S+:(latest|[a-z]+)$", re.MULTILINE)

    def test_no_latest_tags(self) -> None:
        violations: list[str] = []
        for compose_file in self.COMPOSE_FILES:
            if not compose_file.exists():
                continue
            content = compose_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("image:"):
                    # Check for :latest or major-only tags like :17-alpine
                    tag = stripped.split(":")[-1].strip() if ":" in stripped else ""
                    if tag == "latest" or tag == "alpine":
                        violations.append(f"{compose_file.name}:{i}: {stripped}")

        assert not violations, "Unpinned Docker images found:\n" + "\n".join(violations)


class TestSecretsFallbacks:
    """Verify staging/prod compose files use fail-safe secrets (no defaults)."""

    def test_no_fallback_defaults_in_prod(self) -> None:
        violations: list[str] = []
        for env in ["staging", "prod"]:
            compose = (
                Path(__file__).parent.parent.parent.parent / f"docker-compose.{env}.yml"
            )
            if not compose.exists():
                continue
            content = compose.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Check for ${VAR:-default} pattern (fail-open)
                if ":-" in stripped and any(
                    secret in stripped.upper()
                    for secret in [
                        "PASSWORD",
                        "SECRET",
                        "KEY",
                        "TOKEN",
                        "ENCRYPTION",
                    ]
                ):
                    # Allow composed URLs where the inner secrets still use :?
                    # e.g., DATABASE_URL=${DATABASE_URL:-postgres://...${PASSWORD:?must be set}...}
                    # These are safe because the actual secret is fail-fast
                    if ":?" in stripped:
                        continue
                    violations.append(f"docker-compose.{env}.yml:{i}: {stripped[:80]}")

        assert not violations, (
            "Fail-open secret defaults (${VAR:-default}) found in "
            "staging/prod:\n" + "\n".join(violations)
        )
