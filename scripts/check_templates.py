#!/usr/bin/env python3
"""
Static sanity checker for Django templates — does NOT require Django to be
installed (this sandbox can't install it; see README troubleshooting). It
cannot replace actually rendering the templates, but it catches a real,
previously-shipped class of bug: malformed tag delimiters (e.g. `{{%` from
a botched string-substitution script) and unbalanced block/if/for tags,
both of which would only otherwise surface as a TemplateSyntaxError at
first real request — i.e. exactly the kind of thing that must be caught
before calling something "done".

Checks per template file:
  1. No malformed delimiters: `{{%`, `%}}`, `{{#`, `#}}` (valid Django is
     always exactly `{%`, `%}`, `{#`, `#}` — doubled braces are always a bug
     introduced by a templating/substitution mistake, never valid syntax).
  2. Balanced block-level tags: every {% block %} has a matching
     {% endblock %}, every {% if %}/{% for %} has a matching {% endif %}/
     {% endfor %} (ignores {% elif %}/{% else %}, which don't nest).

Usage: python3 scripts/check_templates.py
Exit code 0 = clean. Exit code 1 = at least one problem found.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILES = sorted(REPO_ROOT.glob("templates/**/*.html"))

MALFORMED_PATTERNS = [
    (r"\{\{%", "doubled opening brace before %  (should be `{%`)"),
    (r"%\}\}", "doubled closing brace after %  (should be `%}`)"),
    (r"\{\{#", "doubled opening brace before #  (should be `{#`)"),
    (r"#\}\}", "doubled closing brace after #  (should be `#}`)"),
]

PAIRED_TAGS = {
    "block": "endblock",
    "if": "endif",
    "for": "endfor",
}


def check_malformed_delimiters(path: Path, content: str):
    problems = []
    for pattern, description in MALFORMED_PATTERNS:
        for match in re.finditer(pattern, content):
            line_no = content[: match.start()].count("\n") + 1
            problems.append(f"{path}:{line_no}  {description}")
    return problems


def check_tag_balance(path: Path, content: str):
    problems = []
    tag_re = re.compile(r"\{%\s*(\w+)")
    counts = {tag: 0 for tag in list(PAIRED_TAGS.keys()) + list(PAIRED_TAGS.values())}
    for match in tag_re.finditer(content):
        tag = match.group(1)
        if tag in counts:
            counts[tag] += 1
    for open_tag, close_tag in PAIRED_TAGS.items():
        if counts[open_tag] != counts[close_tag]:
            problems.append(
                f"{path}: unbalanced {{% {open_tag} %}} ({counts[open_tag]}) "
                f"vs {{% {close_tag} %}} ({counts[close_tag]})"
            )
    return problems


def check_empty_tag_placement(path: Path, content: str):
    """{% empty %} is only valid directly inside a {% for %}...{% endfor %}
    block, immediately before the matching {% endfor %} — Django silently
    accepts it in the wrong place at parse time in some versions but the
    loop body after a misplaced {% empty %} never renders as intended.
    This is a heuristic (not a full parser): it flags any {% empty %} whose
    next non-whitespace Django tag is not {% endfor %}."""
    problems = []
    tag_re = re.compile(r"\{%\s*(\w+)[^%]*%\}")
    tags = [(m.group(1), m.start()) for m in tag_re.finditer(content)]
    for i, (tag, pos) in enumerate(tags):
        if tag != "empty":
            continue
        next_tag = tags[i + 1][0] if i + 1 < len(tags) else None
        if next_tag != "endfor":
            line_no = content[:pos].count("\n") + 1
            problems.append(
                f"{path}:{line_no}  {{% empty %}} is not immediately followed by "
                f"{{% endfor %}} (found {{% {next_tag} %}} next) — likely misplaced, "
                f"the empty-state branch may render at the wrong point or never trigger"
            )
    return problems


def check_multiline_comments(path: Path, content: str):
    """
    Regression guard for a real production bug: a multi-line {# ... #}
    Django comment leaked into rendered HTML on the client's server,
    where the browser then partially parsed literal '<script>'-looking
    substrings inside the comment's own explanatory text as real markup.
    Root cause could not be 100% confirmed without running Django (this
    sandbox can't install it), but multi-line comments are the one
    difference between the broken instances and ordinary single-line
    {# ... #} comments elsewhere in the same templates, which were never
    reported as leaking. The fix applied throughout the codebase: every
    {# ... #} comment is single-line, no exceptions. This check enforces
    that permanently, independent of ever fully confirming the Django-
    internals root cause.
    """
    problems = []
    for m in re.finditer(r"\{#.*?#\}", content, re.DOTALL):
        if "\n" in m.group(0):
            line_no = content[: m.start()].count("\n") + 1
            problems.append(
                f"{path}:{line_no}  multi-line {{# #}} comment found — convert to a "
                f"single line (see this function's docstring for why this matters)"
            )
    return problems


def main():
    all_problems = []
    for path in TEMPLATE_FILES:
        content = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT)
        all_problems.extend(check_malformed_delimiters(rel, content))
        all_problems.extend(check_tag_balance(rel, content))
        all_problems.extend(check_empty_tag_placement(rel, content))
        all_problems.extend(check_multiline_comments(rel, content))

    if all_problems:
        print(f"FAILED — checked {len(TEMPLATE_FILES)} templates, found {len(all_problems)} problem(s):")
        for p in all_problems:
            print(f"  {p}")
        return 1

    print(f"OK — checked {len(TEMPLATE_FILES)} templates, no malformed tags or unbalanced block/if/for found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
