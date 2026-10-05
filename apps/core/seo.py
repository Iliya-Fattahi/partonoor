"""
Central SEO helpers. Every public view builds one `seo` dict with `build_seo()`;
`templates/base.html` renders title / description / canonical / robots /
Open Graph / Twitter from it, so no page can silently ship the site-wide defaults.
"""
import re

from django.conf import settings
from django.utils.html import strip_tags

DESC_MAX = 160
TITLE_MAX = 70


def abs_url(path_or_url):
    """Absolute URL on the canonical public host (SITE_URL), never the request host."""
    if not path_or_url:
        return ""
    s = str(path_or_url)
    if s.startswith(("http://", "https://")):
        return s
    if not s.startswith("/"):
        s = "/" + s
    return settings.SITE_URL + s


def clean_text(text, limit=DESC_MAX):
    text = re.sub(r"\s+", " ", strip_tags(str(text or ""))).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip("،,؛;:.-— ")
    return cut + "…"


def _image_url(image):
    try:
        return abs_url(image.url) if image else ""
    except Exception:
        return ""


def build_seo(request, *, title, description="", image=None, og_type="website", robots="",
              canonical_path=None, brand=True, published=None, modified=None, crumbs=None, page=None):
    ss = getattr(request, "site_settings", None)
    brand_name = (ss.company_name_fa if ss else "") or "پرتو نور"
    title = re.sub(r"\s+", " ", strip_tags(title or "")).strip()
    full_title = f"{title} | {brand_name}" if brand and brand_name not in title else title
    path = canonical_path if canonical_path is not None else request.path
    canonical = abs_url(path)
    if page and int(page) > 1:
        canonical += f"?page={int(page)}"
    img = _image_url(image) or _image_url(getattr(ss, "default_og_image", None)) or abs_url("/static/img/og-default.jpg")
    desc = clean_text(description or (ss.default_seo_description if ss else ""))
    seo = {
        "title": full_title,
        "og_title": title,
        "description": desc,
        "canonical": canonical,
        "robots": robots,
        "image": img,
        "og_type": og_type,
        "published": published,
        "modified": modified,
        "brand": brand_name,
    }
    if crumbs:
        from apps.core.structured_data import breadcrumbs_json_ld
        items = [{"name": n, "url": abs_url(u) if u else None} for n, u in crumbs]
        seo["breadcrumb_ld"] = breadcrumbs_json_ld(items)
        seo["breadcrumb_items"] = [{"name": n, "url": u} for n, u in crumbs]
    return seo
