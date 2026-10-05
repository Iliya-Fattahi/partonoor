#!/usr/bin/env python3
"""
Cross-checks every class="..." used across all Django templates against
static/css/main.css. Complements scripts/check_js_css_classes.py (which
checks JS-toggled classes) — this one checks template-authored classes.

Correctly strips whole {% ... %} tag blocks before tokenizing, so
conditional class expressions like class="{% if x %}active{% endif %}"
don't produce bogus "tokens" (an earlier, naive version of this exact
scan split on raw whitespace without stripping tags first, which produced
false positives like ".endif" and ".active_category.slug" — those were
mistaken for missing classes when they were really just fragments of
Django template syntax; this version fixed that class of parsing bug).

Usage: python3 scripts/check_template_css_classes.py
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILES = sorted(REPO_ROOT.glob("templates/**/*.html"))
CSS_FILE = REPO_ROOT / "static/css/main.css"

CLASS_ATTR_RE = re.compile(r'class="([^"]*)"')
DJANGO_TAG_RE = re.compile(r"\{%.*?%\}")


def collect_template_classes():
    usage = {}
    for path in TEMPLATE_FILES:
        content = path.read_text(encoding="utf-8")
        for m in CLASS_ATTR_RE.finditer(content):
            cleaned = DJANGO_TAG_RE.sub(" ", m.group(1))
            for cls in cleaned.split():
                if not cls or "{{" in cls or "}}" in cls:
                    continue  # leftover variable interpolation, e.g. {{ message.tags }}
                usage.setdefault(cls, set()).add(str(path.relative_to(REPO_ROOT)))
    return usage


def css_has_rule(cls: str, css_content: str) -> bool:
    return bool(re.search(r"\." + re.escape(cls) + r"(?=[\s.,:{\[])", css_content))


def main():
    css_content = CSS_FILE.read_text(encoding="utf-8")
    usage = collect_template_classes()
    missing = {cls: files for cls, files in usage.items() if not css_has_rule(cls, css_content)}

    print(f"Checked {len(usage)} distinct classes used across {len(TEMPLATE_FILES)} templates.")
    if missing:
        print(f"FAILED — {len(missing)} class(es) have no CSS rule:")
        for cls, files in sorted(missing.items()):
            print(f"  .{cls}  (used in: {', '.join(sorted(files))})")
        return 1

    print("OK — every template class has a matching CSS rule.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
