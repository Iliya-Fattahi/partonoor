#!/usr/bin/env python3
"""
Catches a specific, previously-real bug class: JavaScript toggles a CSS
class (classList.toggle/add) that no CSS rule ever defines, so the
corresponding UI state (mobile menu open, scrolled header, etc.) silently
does nothing. Two real instances of this were found and fixed during the
Phase 10 audit: .main-nav--open and .is-scrolled.

This is a plain regex scan — no Django, no real CSS parser, no Node
dependency — so it runs anywhere, including this sandbox.

Usage: python3 scripts/check_js_css_classes.py
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_FILES = sorted(REPO_ROOT.glob("static/js/*.js"))
CSS_FILES = sorted(REPO_ROOT.glob("static/css/*.css"))

CLASS_TOGGLE_RE = re.compile(r"classList\.(?:toggle|add)\(\s*['\"]([a-zA-Z0-9_-]+)['\"]")


def find_toggled_classes():
    classes = {}
    for js_file in JS_FILES:
        content = js_file.read_text(encoding="utf-8")
        for match in CLASS_TOGGLE_RE.finditer(content):
            cls = match.group(1)
            classes.setdefault(cls, []).append(js_file.name)
    return classes


def css_has_rule_for(cls: str, css_content: str) -> bool:
    # Matches `.classname` followed by a space, dot, comma, colon, or brace —
    # avoids false-positives like `.classname-extra` matching `.classname`.
    pattern = re.compile(r"\." + re.escape(cls) + r"(?=[\s.,:{\[])")
    return bool(pattern.search(css_content))


def main():
    toggled = find_toggled_classes()
    all_css = "\n".join(f.read_text(encoding="utf-8") for f in CSS_FILES)

    missing = {cls: files for cls, files in toggled.items() if not css_has_rule_for(cls, all_css)}

    if missing:
        print(f"FAILED — {len(missing)} JS-toggled class(es) have no matching CSS rule:")
        for cls, files in missing.items():
            print(f"  .{cls}  (toggled in: {', '.join(files)})")
        print("\nThese classes are set/removed by JavaScript but do nothing visually —")
        print("add a CSS rule for each, or remove the dead JS if the feature was dropped.")
        return 1

    print(f"OK — checked {len(toggled)} JS-toggled class(es) across {len(JS_FILES)} JS files, "
          f"all have a matching CSS rule in {len(CSS_FILES)} CSS file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
