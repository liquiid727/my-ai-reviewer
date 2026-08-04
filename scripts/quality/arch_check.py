#!/usr/bin/env python3
"""Architecture dependency gate (AIP-010 baseline → AIP-011 hardened).

Enforces layering rules from rules/architecture-boundaries.md across:
  Domain, API, Application, Tasks, and a light frontend transport rule.

Static analysis via ast (covers top-level and local/nested imports).
Relative imports are resolved against the importing module path.

Exception registry (arch_exceptions.toml) requires per entry:
  path, rule, owner, reason, expiry, removal_issue
and rejects wildcards, directory-wide paths, missing fields, and expired rows.

Violations print: rule_id, importer path, imported module, line.

Read-only. Exit 0 PASS, 1 FAIL.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

GATE_ID = "architecture"

# (rule_id, layer, forbidden module prefix)
# layer: domain | api | application | tasks | frontend
RULES: list[tuple[str, str, str]] = [
    # ARCH-001 domain purity
    ("domain-no-fastapi", "domain", "fastapi"),
    ("domain-no-celery", "domain", "celery"),
    ("domain-no-sqlalchemy", "domain", "sqlalchemy"),
    ("domain-no-minio", "domain", "minio"),
    ("domain-no-redis", "domain", "redis"),
    ("domain-no-openai", "domain", "openai"),
    ("domain-no-anthropic", "domain", "anthropic"),
    ("domain-no-application", "domain", "backend.application"),
    ("domain-no-infrastructure", "domain", "backend.infrastructure"),
    ("domain-no-api", "domain", "backend.api"),
    ("domain-no-tasks", "domain", "backend.tasks"),
    # ARCH-002 thin API routes (adapter/ORM/task leakage)
    ("api-no-openai", "api", "openai"),
    ("api-no-anthropic", "api", "anthropic"),
    ("api-no-celery", "api", "celery"),
    ("api-no-tasks", "api", "backend.tasks"),
    ("api-no-orm-models", "api", "backend.infrastructure.db.models"),
    ("api-no-storage", "api", "backend.infrastructure.storage"),
    ("api-no-llm", "api", "backend.infrastructure.llm"),
    ("api-no-extractors", "api", "backend.infrastructure.extractors"),
    ("api-no-imaging", "api", "backend.infrastructure.imaging"),
    ("api-no-crypto", "api", "backend.infrastructure.crypto"),
    # ARCH-004 provider SDKs end at infrastructure (application must not import them)
    ("application-no-openai", "application", "openai"),
    ("application-no-anthropic", "application", "anthropic"),
    ("application-no-fastapi", "application", "fastapi"),
    ("application-no-celery", "application", "celery"),
    # ARCH-005 tasks stay free of HTTP framework
    ("tasks-no-fastapi", "tasks", "fastapi"),
]

REQUIRED_EXCEPTION_FIELDS = (
    "path",
    "rule",
    "owner",
    "reason",
    "expiry",
    "removal_issue",
)

WILDCARD_RE = re.compile(r"[*\?\[]")


@dataclass(frozen=True)
class ExceptionEntry:
    path: str
    rule: str
    owner: str
    expiry: date
    reason: str
    removal_issue: str


@dataclass(frozen=True)
class Violation:
    rule: str
    path: str
    line: int
    imported: str
    statement: str


@dataclass(frozen=True)
class RegistryError:
    message: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_simple_toml_tables(text: str, table_name: str) -> list[dict[str, str]]:
    """Minimal TOML table-array parser for [[table_name]] string/scalar fields."""
    tables: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    header = f"[[{table_name}]]"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == header:
            if current is not None:
                tables.append(current)
            current = {}
            continue
        if current is None:
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        current[key] = value
    if current is not None:
        tables.append(current)
    return tables


def load_exceptions(path: Path) -> tuple[list[ExceptionEntry], list[RegistryError]]:
    """Load and validate exception registry. Invalid entries become RegistryErrors."""
    if not path.is_file():
        return [], []
    raw_tables = _parse_simple_toml_tables(path.read_text(encoding="utf-8"), "exceptions")
    out: list[ExceptionEntry] = []
    errors: list[RegistryError] = []
    known_rules = {rid for rid, _, _ in RULES} | {
        "frontend-page-no-raw-fetch",
    }

    for idx, raw in enumerate(raw_tables, start=1):
        missing = [f for f in REQUIRED_EXCEPTION_FIELDS if not str(raw.get(f, "")).strip()]
        if missing:
            errors.append(
                RegistryError(
                    f"exceptions[{idx}]: missing required fields {missing}; got keys={sorted(raw)}"
                )
            )
            continue

        rel_path = str(raw["path"]).replace("\\", "/").strip()
        rule = str(raw["rule"]).strip()
        owner = str(raw["owner"]).strip()
        reason = str(raw["reason"]).strip()
        removal_issue = str(raw["removal_issue"]).strip()
        expiry_raw = str(raw["expiry"]).strip()

        if WILDCARD_RE.search(rel_path) or rel_path.endswith("/") or rel_path.endswith("/**"):
            errors.append(
                RegistryError(
                    f"exceptions[{idx}]: wildcard/directory-wide path rejected: {rel_path!r}"
                )
            )
            continue
        if not rel_path.endswith(".py") and not rel_path.endswith((".ts", ".tsx")):
            errors.append(
                RegistryError(
                    f"exceptions[{idx}]: path must be an exact source file "
                    f"(.py/.ts/.tsx), got {rel_path!r}"
                )
            )
            continue
        if rule not in known_rules:
            errors.append(
                RegistryError(
                    f"exceptions[{idx}]: unknown rule {rule!r} for path {rel_path}"
                )
            )
            continue
        if owner.lower() in {"", "unassigned", "tbd", "todo", "none"}:
            errors.append(
                RegistryError(
                    f"exceptions[{idx}]: owner must be a real owner/issue, got {owner!r}"
                )
            )
            continue
        if not re.search(r"#\d+|AIP-\d+|RIP-\d+", removal_issue):
            errors.append(
                RegistryError(
                    f"exceptions[{idx}]: removal_issue must reference an issue "
                    f"(#NNN / AIP-NNN / RIP-NNN), got {removal_issue!r}"
                )
            )
            continue
        try:
            expiry = date.fromisoformat(expiry_raw)
        except ValueError:
            errors.append(
                RegistryError(
                    f"exceptions[{idx}]: invalid expiry {expiry_raw!r} (want YYYY-MM-DD)"
                )
            )
            continue

        out.append(
            ExceptionEntry(
                path=rel_path,
                rule=rule,
                owner=owner,
                expiry=expiry,
                reason=reason,
                removal_issue=removal_issue,
            )
        )
    return out, errors


def _module_matches(imported: str, forbidden: str) -> bool:
    return imported == forbidden or imported.startswith(forbidden + ".")


def _pkg_parts_for_file(rel_posix: str) -> list[str]:
    """backend/domain/jd/services.py → ['backend','domain','jd']"""
    p = Path(rel_posix)
    parts = list(p.parts[:-1])  # drop filename
    return parts


def _resolve_from_import(rel_posix: str, module: str | None, level: int) -> str | None:
    """Resolve ImportFrom to absolute dotted module path when possible."""
    if level == 0:
        return module
    pkg = _pkg_parts_for_file(rel_posix)
    # level 1 = current package; level 2 = parent, etc.
    if level > len(pkg) + 1:
        return module  # best-effort
    base = pkg[: len(pkg) - (level - 1)] if level > 0 else pkg
    if module:
        return ".".join([*base, *module.split(".")])
    return ".".join(base) if base else None


def _iter_import_events(
    tree: ast.AST, rel_posix: str
) -> list[tuple[int, str, str]]:
    """Return list of (lineno, imported_module, statement_snippet_ready).

    For ``from pkg import name`` also emit ``pkg.name`` so rules that target
    a submodule (e.g. ``backend.infrastructure.db.models``) catch
    ``from backend.infrastructure.db import models``.
    """
    events: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                events.append((node.lineno or 0, alias.name, alias.name))
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_from_import(rel_posix, node.module, node.level or 0)
            if resolved:
                events.append((node.lineno or 0, resolved, resolved))
            # Also resolve imported names as potential submodules.
            # Skip star-imports (no concrete name) and pure attribute imports
            # when the parent already fully identifies the forbidden module —
            # still emit pkg.name so leaf rules match.
            if resolved and node.names:
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    leaf = f"{resolved}.{alias.name}"
                    events.append((node.lineno or 0, leaf, leaf))
    return events


def scan_python_file(path: Path, rel: str, layer: str) -> list[Violation]:
    try:
        src = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Violation(rule="io-error", path=rel, line=0, imported="", statement=str(exc))]
    try:
        tree = ast.parse(src, filename=rel)
    except SyntaxError as exc:
        return [
            Violation(
                rule="syntax-error",
                path=rel,
                line=exc.lineno or 0,
                imported="",
                statement=exc.msg,
            )
        ]

    applicable = [(rid, forb) for rid, lay, forb in RULES if lay == layer]
    lines = src.splitlines()
    violations: list[Violation] = []
    for lineno, mod, _ in _iter_import_events(tree, rel):
        for rule_id, forbidden in applicable:
            if _module_matches(mod, forbidden):
                stmt = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else mod
                violations.append(
                    Violation(
                        rule=rule_id,
                        path=rel,
                        line=lineno,
                        imported=mod,
                        statement=stmt,
                    )
                )
    return violations


def scan_layer(backend: Path, layer: str) -> list[Violation]:
    root = backend / layer
    if not root.is_dir():
        return []
    found: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(backend.parent).as_posix()
        found.extend(scan_python_file(path, rel, layer))
    return found


_FETCH_RE = re.compile(r"\bfetch\s*\(")
_API_IMPORT_RE = re.compile(
    r"""from\s+['"]@/api(?:/[^'"]*)?['"]|import\s+['"]@/api(?:/[^'"]*)?['"]"""
)


def scan_frontend_pages(frontend_src: Path) -> list[Violation]:
    """ARCH-007 light check: pages with fetch() must import from @/api."""
    if not frontend_src.is_dir():
        return []
    pages_dirs = [
        frontend_src / "pages",
        frontend_src,
    ]
    candidates: list[Path] = []
    seen: set[Path] = set()
    for base in pages_dirs:
        if not base.is_dir():
            continue
        patterns = ("*Page.tsx", "*Page.ts", "pages/**/*.tsx", "pages/**/*.ts")
        if base.name == "pages":
            for p in base.rglob("*.tsx"):
                if p not in seen:
                    seen.add(p)
                    candidates.append(p)
            for p in base.rglob("*.ts"):
                if p not in seen:
                    seen.add(p)
                    candidates.append(p)
        else:
            for p in base.glob("*Page.tsx"):
                if p not in seen:
                    seen.add(p)
                    candidates.append(p)

    violations: list[Violation] = []
    root = frontend_src.parent.parent  # repo root if frontend/src
    # frontend_src is .../frontend/src → parent is frontend, parent.parent is repo
    for path in sorted(candidates):
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not _FETCH_RE.search(src):
            continue
        if _API_IMPORT_RE.search(src):
            continue
        # allow test files
        if ".test." in path.name or path.name.endswith(".spec.tsx"):
            continue
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = path.as_posix()
        # find first fetch line
        line_no = 0
        for i, line in enumerate(src.splitlines(), start=1):
            if _FETCH_RE.search(line):
                line_no = i
                break
        violations.append(
            Violation(
                rule="frontend-page-no-raw-fetch",
                path=rel,
                line=line_no,
                imported="fetch",
                statement="fetch() without @/api import",
            )
        )
    return violations


def _dedupe(violations: list[Violation]) -> list[Violation]:
    seen: set[tuple[str, str, int, str]] = set()
    unique: list[Violation] = []
    for v in violations:
        key = (v.rule, v.path, v.line, v.imported)
        if key in seen:
            continue
        seen.add(key)
        unique.append(v)
    return unique


def run_check(
    root: Path | None = None,
    *,
    exceptions_path: Path | None = None,
    today: date | None = None,
) -> tuple[int, list[str], list[str]]:
    """Run the gate. Returns (exit_code, stdout_lines, stderr_lines)."""
    root = root or repo_root()
    backend = root / "backend"
    exc_path = exceptions_path or (Path(__file__).resolve().parent / "arch_exceptions.toml")
    today = today or datetime.now(timezone.utc).date()

    out: list[str] = []
    err: list[str] = []

    def o(msg: str) -> None:
        out.append(msg)

    def e(msg: str) -> None:
        err.append(msg)

    o(f"==> [{GATE_ID}] python {Path(__file__).resolve().name}")
    try:
        rel_exc = exc_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel_exc = str(exc_path)
    o(f"==> [{GATE_ID}] exceptions {rel_exc}")

    exceptions, registry_errors = load_exceptions(exc_path)

    rc = 0
    if registry_errors:
        rc = 1
        e(f"FAIL [{GATE_ID}] invalid exception registry entries:")
        for re_err in registry_errors:
            e(f"  - {re_err.message}")

    expired = [ex for ex in exceptions if ex.expiry < today]
    active = [ex for ex in exceptions if ex.expiry >= today]
    active_keys = {(ex.path, ex.rule) for ex in active}

    violations = _dedupe(
        scan_layer(backend, "domain")
        + scan_layer(backend, "api")
        + scan_layer(backend, "application")
        + scan_layer(backend, "tasks")
        + scan_frontend_pages(root / "frontend" / "src")
    )

    new_violations = [v for v in violations if (v.path, v.rule) not in active_keys]
    covered = [v for v in violations if (v.path, v.rule) in active_keys]

    used_keys = {(v.path, v.rule) for v in violations}
    unused = [ex for ex in active if (ex.path, ex.rule) not in used_keys]

    if expired:
        rc = 1
        e(f"FAIL [{GATE_ID}] expired exception entries:")
        for ex in expired:
            e(
                f"  - {ex.path} rule={ex.rule} owner={ex.owner} "
                f"removal={ex.removal_issue} expired={ex.expiry.isoformat()} "
                f"reason={ex.reason}"
            )

    if new_violations:
        rc = 1
        e(f"FAIL [{GATE_ID}] architecture violations:")
        for v in new_violations:
            e(
                f"  - rule={v.rule} importer={v.path}:{v.line} "
                f"imported={v.imported} :: {v.statement}"
            )

    if covered:
        o(f"INFO [{GATE_ID}] waived pre-existing violations ({len(covered)}):")
        for v in covered:
            o(f"  - rule={v.rule} importer={v.path}:{v.line} imported={v.imported}")

    if unused:
        o(f"INFO [{GATE_ID}] unused exception entries ({len(unused)}):")
        for ex in unused:
            o(
                f"  - {ex.path} rule={ex.rule} owner={ex.owner} "
                f"removal={ex.removal_issue}"
            )

    o(
        f"INFO [{GATE_ID}] scanned domain+api+application+tasks+frontend-pages; "
        f"violations={len(violations)} new={len(new_violations)} "
        f"waived={len(covered)} expired={len(expired)} "
        f"registry_errors={len(registry_errors)}"
    )

    if rc == 0:
        o(f"PASS [{GATE_ID}]")
    else:
        e(f"FAIL [{GATE_ID}] exit=1")
    return rc, out, err


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Architecture dependency gate")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root (default: auto-detect from script location)",
    )
    parser.add_argument(
        "--exceptions",
        type=Path,
        default=None,
        help="path to arch_exceptions.toml",
    )
    args = parser.parse_args(argv)
    rc, out, err = run_check(root=args.root, exceptions_path=args.exceptions)
    for line in out:
        print(line)
    for line in err:
        print(line, file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
