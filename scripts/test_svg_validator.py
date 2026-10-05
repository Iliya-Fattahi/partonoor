#!/usr/bin/env python3
"""
Real, runnable security test for apps.core.validators.validate_svg_file's
detection logic — needs only defusedxml (available in this sandbox), NOT
Django, so it actually executes here (unlike the Django-dependent
apps/core/tests.py, which is written but blocked from running until a real
Django environment is available).

This mirrors the exact scanning logic in validate_svg_file (kept in sync
manually — if you change the dangerous-tag/attribute lists there, update
MALICIOUS_SVGS/SAFE_SVGS here too and re-run).

Run: python3 scripts/test_svg_validator.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import defusedxml.ElementTree as DefusedET

DANGEROUS_TAGS = ("script", "foreignobject", "iframe", "embed", "object")
DANGEROUS_ATTR_PREFIXES = ("on",)
DANGEROUS_VALUE_SUBSTRINGS = ("javascript:", "data:text/html")

MALICIOUS_SVGS = {
    "inline <script>": b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(document.cookie)</script></svg>',
    "onload event handler": b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><circle r="10"/></svg>',
    "javascript: URI in href": b'<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><text>click</text></a></svg>',
    "encoded data:text/html payload": b'<svg xmlns="http://www.w3.org/2000/svg"><image href="data:text/html,%3Cscript%3Ealert(1)%3C/script%3E"/></svg>',
    "XXE via external entity": (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>'
    ),
    "nested foreignObject with script": (
        b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><script>alert(1)</script></foreignObject></svg>'
    ),
}

SAFE_SVGS = {
    "simple circle": b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="red"/></svg>',
    "path-based icon": b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M10 10 H 90 V 90 H 10 Z" fill="none" stroke="black"/></svg>',
    "gradient fill (real-world logo pattern)": (
        b'<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"><stop offset="0" stop-color="#fff"/>'
        b'<stop offset="1" stop-color="#000"/></linearGradient></defs><rect fill="url(#g)" width="100" height="100"/></svg>'
    ),
}


def scan(raw: bytes) -> str:
    """Mirrors validate_svg_file's decision logic; returns 'BLOCKED: <reason>' or 'ALLOWED'."""
    try:
        root = DefusedET.fromstring(raw)
    except Exception as e:
        return f"BLOCKED: invalid/malformed XML ({type(e).__name__})"
    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()
        if tag in DANGEROUS_TAGS:
            return f"BLOCKED: dangerous tag <{tag}>"
        for attr_name, attr_value in element.attrib.items():
            local_attr = attr_name.split("}")[-1].lower()
            if any(local_attr.startswith(p) for p in DANGEROUS_ATTR_PREFIXES):
                return f"BLOCKED: event handler attribute '{local_attr}'"
            value_lower = (attr_value or "").lower()
            if any(s in value_lower for s in DANGEROUS_VALUE_SUBSTRINGS):
                return "BLOCKED: dangerous value in attribute"
    return "ALLOWED"


def main():
    failures = 0

    print("-- Malicious SVGs (must all be BLOCKED) --")
    for name, payload in MALICIOUS_SVGS.items():
        result = scan(payload)
        ok = result.startswith("BLOCKED")
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {result}")
        if not ok:
            failures += 1

    print("\n-- Legitimate SVGs (must all be ALLOWED) --")
    for name, payload in SAFE_SVGS.items():
        result = scan(payload)
        ok = result == "ALLOWED"
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {result}")
        if not ok:
            failures += 1

    total = len(MALICIOUS_SVGS) + len(SAFE_SVGS)
    print(f"\n{total - failures}/{total} assertions passed.")
    if failures:
        print("SECURITY TEST FAILED — do not consider the SVG validator safe until this is fixed.")
        sys.exit(1)
    print("ALL SVG VALIDATOR SECURITY TESTS PASSED.")


if __name__ == "__main__":
    main()
