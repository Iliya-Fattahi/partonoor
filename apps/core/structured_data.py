r"""
Builds JSON-LD structured data as real Python dicts (via json.dumps), never
as hand-rolled string concatenation in a template — that approach is
fundamentally fragile (a single unescaped quote in a project title breaks
the JSON) and was the design used in an earlier, broken draft of this
feature that has been removed.

Every builder here returns a ready-to-embed JSON string. `</` is escaped to
`<\/` before embedding, because a value containing the literal text
"</script>" (e.g. someone pastes it into a project title) would otherwise
prematurely close the surrounding <script> tag — a real, if obscure, XSS
vector for any JSON-LD implementation that skips this step.
"""
import json

from .seo import abs_url


def render_json_ld(data: dict) -> str:
    json_str = json.dumps(data, ensure_ascii=False)
    return json_str.replace("</", "<\\/")


def _img(field):
    try:
        return abs_url(field.url) if field else None
    except Exception:
        return None


def _image_object(field, caption=""):
    url = _img(field)
    if not url:
        return None
    obj = {"@type": "ImageObject", "url": url, "contentUrl": url}
    try:
        obj["width"], obj["height"] = field.width, field.height
    except Exception:
        pass
    if caption:
        obj["caption"] = caption
    return obj


ORG_ID = abs_url("/#organization")


def organization_json_ld(site_settings) -> str:
    """Organization + WebSite (with site search) as one @graph. Only fields the client actually filled in."""
    org = {
        "@type": "Organization",
        "@id": ORG_ID,
        "name": site_settings.company_name_fa,
        "url": abs_url("/"),
    }
    if site_settings.company_name_en:
        org["alternateName"] = site_settings.company_name_en
    logo = _img(site_settings.logo_full) or _img(site_settings.logo_symbol)
    if logo:
        org["logo"] = {"@type": "ImageObject", "url": logo}
    if site_settings.phone_international:
        org["telephone"] = "+" + site_settings.phone_international
    same_as = [u for u in (site_settings.instagram_url, site_settings.telegram_link, site_settings.whatsapp_link) if u]
    if same_as:
        org["sameAs"] = same_as
    description = site_settings.default_seo_description or site_settings.slogan
    if description:
        org["description"] = description
    website = {
        "@type": "WebSite",
        "@id": abs_url("/#website"),
        "url": abs_url("/"),
        "name": site_settings.company_name_fa,
        "inLanguage": "fa-IR",
        "publisher": {"@id": ORG_ID},
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": abs_url("/search/") + "?q={search_term_string}"},
            "query-input": "required name=search_term_string",
        },
    }
    return render_json_ld({"@context": "https://schema.org", "@graph": [org, website]})


def breadcrumbs_json_ld(items: list) -> str:
    """items: list of {"name": str, "url": str|None} — last item's url may be None (current page)."""
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": item["name"],
                **({"item": item["url"]} if item.get("url") else {}),
            }
            for i, item in enumerate(items)
        ],
    }
    return render_json_ld(data)


def article_json_ld(article, site_settings, request) -> str:
    url = abs_url(article.get_absolute_url())
    image = _image_object(article.cover_image, article.title)
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.title[:110],
        "description": article.seo_description or article.excerpt,
        "image": [image["url"]] if image else None,
        "datePublished": article.published_at.isoformat() if article.published_at else None,
        "dateModified": article.updated_at.isoformat(),
        "inLanguage": "fa-IR",
        "publisher": {"@id": ORG_ID},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "url": url,
    }
    if article.category_id:
        data["articleSection"] = article.category.title
    tags = [t.title for t in article.tags.all()]
    if tags:
        data["keywords"] = ", ".join(tags)
    if article.author_name:
        name, _sep, role = article.author_name.partition(" — ")
        person = {"@type": "Person", "name": name.strip()}
        if role.strip():
            person["jobTitle"] = role.strip()
        data["author"] = person
    elif article.author_id:
        data["author"] = {"@type": "Person", "name": article.author.get_full_name() or article.author.username}
    else:
        data["author"] = {"@id": ORG_ID}
    data = {k: v for k, v in data.items() if v is not None}
    return render_json_ld(data)


def product_json_ld(product, site_settings) -> str:
    imgs = [_img(product.main_image)] if product.main_image else []
    imgs += [u for u in (_img(i.image) for i in product.images.all()) if u]
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.title,
        "description": product.seo_description or product.short_description,
        "url": abs_url(product.get_absolute_url()),
        "image": [u for u in dict.fromkeys(imgs) if u] or None,
        "brand": {"@type": "Brand", "name": site_settings.company_name_fa},
        "manufacturer": {"@id": ORG_ID},
    }
    data = {k: v for k, v in data.items() if v is not None}
    return render_json_ld(data)


def project_json_ld(project, site_settings, gallery_images=()) -> str:
    imgs = [o for o in (_image_object(project.cover_image, project.title),) if o]
    for im in list(gallery_images)[:8]:
        o = _image_object(im.image, im.alt_text or "")
        if o:
            imgs.append(o)
    data = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": project.title,
        "description": project.seo_description or project.short_description,
        "url": abs_url(project.get_absolute_url()),
        "image": imgs or None,
        "creator": {"@id": ORG_ID},
        "inLanguage": "fa-IR",
    }
    if project.city or project.location:
        data["locationCreated"] = {"@type": "Place", "name": project.city or project.location}
    if project.year:
        data["dateCreated"] = str(project.year)
    data = {k: v for k, v in data.items() if v is not None}
    return render_json_ld(data)


def service_json_ld(service, site_settings) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": service.title,
        "description": service.seo_description or service.short_description,
        "url": abs_url(service.get_absolute_url()),
        "provider": {"@id": ORG_ID},
        "areaServed": {"@type": "Country", "name": "ایران"},
    }
    return render_json_ld(data)


def collection_json_ld(category, items, url) -> str:
    imgs = [o for o in (_image_object(i.image, i.alt_text or i.title) for i in items[:12] if i.image) if o]
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": category.title,
        "url": url,
        "inLanguage": "fa-IR",
        "isPartOf": {"@id": abs_url("/#website")},
        "about": category.title,
    }
    if category.description:
        data["description"] = category.description
    if imgs:
        data["image"] = imgs
    return render_json_ld(data)
