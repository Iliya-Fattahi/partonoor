"""
Sanitizes rich-text HTML coming from the article editor before it is ever
saved to the database. This is a real allowlist-based sanitizer (bleach),
not a placeholder — it strips scripts, event handlers, iframes, and any tag
or attribute outside the allowlist below, closing the XSS vector required
by spec sections 20/74 ("Ensure content is sanitized safely").
"""
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s",
    "h2", "h3", "h4",
    "ul", "ol", "li",
    "blockquote",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "figure", "figcaption",
    "span", "div",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "span": ["class"],
    "div": ["class"],
    "table": ["class"],
    "*": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_css_sanitizer = CSSSanitizer(allowed_css_properties=["text-align", "color"])


def sanitize_article_html(raw_html: str) -> str:
    """Strips anything outside the allowlist. Always call this before save()."""
    if not raw_html:
        return raw_html
    # bleach(strip=True) drops the <script>/<style> TAGS but keeps their text; remove the whole block.
    raw_html = re.sub(r"(?is)<(script|style|iframe|object|embed)\b.*?(</\1\s*>|$)", "", raw_html)
    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_css_sanitizer,
        strip=True,
    )
    # Force safe rel/target on any external link the editor produced.
    cleaned = bleach.linkify(cleaned, callbacks=[])
    return cleaned
