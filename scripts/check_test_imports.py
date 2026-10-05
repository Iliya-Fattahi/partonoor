#!/usr/bin/env python3
"""
py_compile only catches SYNTAX errors. It cannot catch `ImportError:
cannot import name X from Y` — which happens when a test file imports a
function/class that was renamed, removed, or never existed. A single such
error in ANY test module can make Django's test loader abort before
collecting tests from that module, which is one real, common cause behind
a report of "0 tests" or "test discovery failed" that looks confusing
without a full traceback.

This script statically resolves every `from apps.X.Y import A, B` (and
`from .Y import A, B`) import found in every apps/*/tests*.py file against
the ACTUAL names defined in the target module (via AST — no execution, so
it works without Django installed), and flags any name that doesn't exist
there. It does not attempt every possible import form (e.g., `import X`
alone, star imports) — those are rarer sources of this specific bug class
and are left to Django's own real import machinery to catch on your
system.

Usage: python3 scripts/check_test_imports.py
"""
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def defined_names(module_path: Path) -> set:
    """Every top-level name that `from module import X` could resolve to:
    classes, functions, and simple assignments (e.g. `variant_path = ...`,
    `NAV_CACHE_KEY = ...`), plus names brought in via other imports in that
    module (so `from .models import Foo` in a __init__-less chain still
    resolves) — kept intentionally simple/best-effort."""
    if not module_path.exists():
        return None  # signal "module file not found" distinctly from "found, but empty"
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def resolve_module_path(app_pkg_dir: Path, module_dotted: str, level: int) -> Path:
    """Best-effort translation of an import's module path to a file on disk.
    Handles `apps.core.models` (absolute) and `.models` / `..core.models`
    (relative, level = number of leading dots) forms."""
    if level == 0:
        parts = module_dotted.split(".")
        return REPO_ROOT.joinpath(*parts).with_suffix(".py")
    # relative import: level=1 means "current package" (the app dir itself)
    base = app_pkg_dir
    for _ in range(level - 1):
        base = base.parent
    if module_dotted:
        base = base.joinpath(*module_dotted.split("."))
    return base.with_suffix(".py")


def check_file(path: Path):
    problems = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    app_pkg_dir = path.parent

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module is None and node.level == 0:
            continue  # `from . import x` with nothing else — skip, rare and ambiguous to resolve generically
        module_dotted = node.module or ""
        target_path = resolve_module_path(app_pkg_dir, module_dotted, node.level)

        # Only check imports that resolve inside this repo (skip django.*, etc.)
        try:
            target_path.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if not str(target_path).replace(str(REPO_ROOT), "").lstrip("/\\").startswith("apps"):
            continue

        names = defined_names(target_path)
        if names is None:
            # Could be a package import (directory with __init__.py) rather than a module file
            init_path = target_path.with_suffix("") / "__init__.py"
            if init_path.exists():
                names = defined_names(init_path)
            if names is None:
                problems.append(f"{path}:{node.lineno}  cannot resolve module for 'from {module_dotted} import ...' (looked for {target_path})")
                continue

        for alias in node.names:
            if alias.name == "*":
                continue
            if alias.name not in names:
                problems.append(
                    f"{path}:{node.lineno}  'from {'.' * node.level}{module_dotted} import {alias.name}' "
                    f"— '{alias.name}' not found in {target_path.relative_to(REPO_ROOT)}"
                )
    return problems


def main():
    all_problems = []
    for path in sorted(REPO_ROOT.glob("apps/*/test*.py")) + sorted(REPO_ROOT.glob("apps/*/tests/test_*.py")):
        all_problems.extend(check_file(path))

    if all_problems:
        print(f"FAILED — {len(all_problems)} unresolved import(s) found:")
        for p in all_problems:
            print(f"  {p}")
        return 1

    test_files = list(REPO_ROOT.glob("apps/*/test*.py")) + list(REPO_ROOT.glob("apps/*/tests/test_*.py"))
    print(f"OK — checked {len(test_files)} test files, every 'from apps.X import Y' resolves to a real name.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
