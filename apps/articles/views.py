import uuid
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.core.validators import validate_image_file
from django.urls import reverse
from django.shortcuts import get_object_or_404, render

from apps.core.seo import build_seo
from apps.core.structured_data import article_json_ld

import os
import re

from django.db.models import Q

from django.utils.html import strip_tags
from django.utils.text import slugify

from .models import Article, ArticleCategory, Tag


def _add_toc(html):
    """Give every <h2> a stable id and return (html_with_ids, toc_items) for the sticky table of contents."""
    toc, used = [], set()

    def repl(m):
        text = strip_tags(m.group(2)).strip()
        base = slugify(text, allow_unicode=True)[:60] or f"s{len(toc) + 1}"
        slug, n = base, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        toc.append({"id": slug, "title": text})
        return f'<h2{m.group(1)} id="{slug}">{m.group(2)}</h2>'

    return re.sub(r"<h2([^>]*)>(.*?)</h2>", repl, html, flags=re.S), toc


def _prepare_body_images(html):
    """Inline article images: lazy-load, async decode and intrinsic width/height (no layout shift)."""
    from django.conf import settings
    from PIL import Image

    def repl(m):
        tag = m.group(0)
        if "loading=" not in tag:
            tag = tag.replace("<img", '<img loading="lazy" decoding="async"', 1)
        if "width=" not in tag:
            src = re.search(r'src="([^"]+)"', tag)
            if src and src.group(1).startswith(settings.MEDIA_URL):
                path = os.path.join(str(settings.MEDIA_ROOT), src.group(1)[len(settings.MEDIA_URL):])
                try:
                    with Image.open(path) as im:
                        tag = tag.replace("<img", f'<img width="{im.width}" height="{im.height}"', 1)
                except Exception:
                    pass
        return tag

    return re.sub(r"<img\b[^>]*>", repl, html)


def article_list(request):
    articles = Article.objects.filter(published=True).select_related("category", "author").prefetch_related("tags")

    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        articles = articles.filter(Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(content__icontains=q))

    category_slug = request.GET.get("category")
    active_category = None
    if category_slug:
        active_category = get_object_or_404(ArticleCategory, slug=category_slug)
        articles = articles.filter(category=active_category)

    tag_slug = request.GET.get("tag")
    active_tag = None
    if tag_slug:
        active_tag = get_object_or_404(Tag, slug=tag_slug)
        articles = articles.filter(tags=active_tag)

    paginator = Paginator(articles, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Filtered / searched views are thin duplicates of the list: keep them out of the index, canonical -> list.
    filtered = bool(q or active_category or active_tag)
    seo = build_seo(
        request,
        title=(f"مقالات با برچسب «{active_tag.title}»" if active_tag else "مجله‌ی نورپردازی شهری؛ مقالات تخصصی"),
        description="مقالات تخصصی پرتو نور درباره‌ی نورپردازی شهری: طراحی نور، انرژی و آلودگی نوری، هویت شبانه‌ی شهر و فناوری‌های نوین.",
        robots="noindex, follow" if filtered else "",
        canonical_path=reverse("articles:list") if filtered else None,
        page=page_obj.number, crumbs=[("خانه", "/"), ("مقالات", None)],
    )
    return render(request, "articles/article_list.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"], "active_tag": active_tag,
        "page_obj": page_obj,
        "categories": ArticleCategory.objects.all(),
        "active_category": active_category,
        "q": q,
    })


def article_detail(request, slug):
    article = get_object_or_404(
        Article.objects.select_related("category", "author").prefetch_related("tags"),
        slug=slug, published=True,
    )
    from django.db.models import Count
    related = (Article.objects.filter(published=True).exclude(pk=article.pk)
               .annotate(shared=Count("tags", filter=Q(tags__in=article.tags.all())))
               .order_by("-shared", "-published_at")[:3])
    seo = build_seo(
        request,
        title=article.seo_title or article.title,
        description=article.seo_description or article.excerpt,
        image=article.seo_image or article.cover_image, og_type="article",
        published=article.published_at, modified=article.updated_at,
        crumbs=[("خانه", "/"), ("مقالات", reverse("articles:list")), (article.title, None)],
    )
    breadcrumb_items = seo["breadcrumb_items"]

    body_html, toc = _add_toc(article.content)
    body_html = _prepare_body_images(body_html)
    words = len(strip_tags(article.content).split())
    return render(request, "articles/article_detail.html", {
        "article": article,
        "body_html": body_html,
        "toc": toc,
        "reading_minutes": max(1, round(words / 180)),
        "related": related,
        "featured_project": __import__("apps.projects.models", fromlist=["Project"]).Project.objects.filter(featured=True, published=True).first(),
        "json_ld": article_json_ld(article, request.site_settings, request),
        "seo": seo,
        "breadcrumb_items": breadcrumb_items,
    })


@require_POST
@staff_member_required
def upload_inline_image(request):
    """Staff-only: stores an image used inside an article body (Quill editor) and returns its URL."""
    upload = request.FILES.get("image")
    if not upload:
        return JsonResponse({"error": "فایلی ارسال نشد."}, status=400)
    try:
        validate_image_file(upload)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)
    ext = Path(upload.name).suffix.lower() or ".jpg"
    saved = default_storage.save(f"articles/inline/{uuid.uuid4().hex}{ext}", upload)
    return JsonResponse({"url": default_storage.url(saved)})
