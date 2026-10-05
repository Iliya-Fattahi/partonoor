#!/usr/bin/env python3
"""
Static regression guard for the admin-registry bug (PartoNoorAdminSite._registry
was empty because every app used the bare @admin.register(Model) decorator,
which always targets django.contrib.admin.site — never our custom site).

This does NOT require Django/Postgres to run — it's a plain-text/AST scan of
every apps/*/admin.py file, so it can run in any environment including this
sandbox, and should also run as a pre-commit / CI check in the real repo.

Usage: python3 scripts/check_admin_registration.py
Exit code 0 = all @admin.register(...) calls include site=partonoor_admin_site.
Exit code 1 = at least one violation found (prints file:line).
"""
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADMIN_FILES = sorted(REPO_ROOT.glob("apps/*/admin.py"))


def find_violations(path: Path):
    violations = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for deco in node.decorator_list:
            if not (isinstance(deco, ast.Call) and _is_admin_register(deco.func)):
                continue
            has_site_kwarg = any(kw.arg == "site" for kw in deco.keywords)
            if not has_site_kwarg:
                violations.append((path, deco.lineno, node.name))
    return violations


def _is_admin_register(func_node) -> bool:
    # matches `admin.register(...)`
    return (
        isinstance(func_node, ast.Attribute)
        and func_node.attr == "register"
        and isinstance(func_node.value, ast.Name)
        and func_node.value.id == "admin"
    )


def main():
    all_violations = []
    for path in ADMIN_FILES:
        all_violations.extend(find_violations(path))

    if all_violations:
        print("FAILED — the following ModelAdmins are NOT registered on partonoor_admin_site:")
        for path, lineno, class_name in all_violations:
            rel = path.relative_to(REPO_ROOT)
            print(f"  {rel}:{lineno}  class {class_name}  ->  missing site=partonoor_admin_site")
        print(
            "\nFix: add `site=partonoor_admin_site` to the @admin.register(...) call, "
            "and `from apps.core.admin_site import partonoor_admin_site` at the top of the file."
        )
        return 1

    print(f"OK — checked {len(ADMIN_FILES)} admin.py files, all registrations target partonoor_admin_site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
