from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.seo import build_seo, clean_text

from .models import GalleryItem, WorkCategory

PUBLIC = Q(is_visible=True, needs_review=False, category__isnull=False, category__published=True)


def public_categories():
    """Published categories that have at least one visible work, with a cover image URL, count and URL."""
    cats = WorkCategory.objects.filter(published=True).annotate(
        count=Count("items", filter=Q(items__is_visible=True, items__needs_review=False))
    ).filter(count__gt=0)
    result = []
    for cat in cats:
        cover = cat.items.filter(is_visible=True, needs_review=False, media_type="image").exclude(image="").first()
        cat.cover_url = cover.image.url if cover else ""
        cat.url = reverse("gallery:category", kwargs={"slug": cat.slug})
        result.append(cat)
    return result


def _items():
    return GalleryItem.objects.filter(PUBLIC).select_related("category", "project").order_by(
        "category__display_order", "display_order", "id")


def gallery_view(request):
    # Old filter URLs (/gallery/?category=slug) now live on real category pages.
    legacy = request.GET.get("category")
    if legacy:
        if WorkCategory.objects.filter(slug=legacy, published=True).exists():
            return redirect(reverse("gallery:category", kwargs={"slug": legacy}), permanent=True)
        return redirect(reverse("gallery:index"), permanent=True)

    categories = public_categories()
    items = list(_items())
    groups = [{"category": c, "items": [i for i in items if i.category_id == c.id][:6]} for c in categories]
    first_img = next((i.image for i in items if i.image), None)
    seo = build_seo(
        request,
        title="آثار و نمونه کارها: المان نوری و نورپردازی شهری",
        description="نمونه کارهای پرتو نور: المان‌های نوری داستانی، لوسترهای نوری شهری، ریسه‌های نوری عرض خیابانی و المان‌های زمینی و مناسبتی.",
        image=first_img,
        crumbs=[("خانه", "/"), ("آثار", None)],
    )
    return render(request, "gallery/gallery.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"],
        "groups": groups, "categories": categories, "total": len(items),
    })


def category_view(request, slug):
    category = next((c for c in public_categories() if c.slug == slug), None)
    if category is None:
        raise Http404
    items = [i for i in _items() if i.category_id == category.id]
    cover = next((i.image for i in items if i.image), None)
    base_desc = category.description or f"نمونه‌هایی از {category.title} ساخته‌شده و اجراشده توسط پرتو نور."
    seo = build_seo(
        request,
        title=category.seo_title or f"{category.title}؛ نمونه کار پرتو نور",
        description=category.seo_description or clean_text(f"{base_desc} مشاهده‌ی {category.count} اثر و درخواست مشاوره برای پروژه‌ی شما."),
        image=cover,
        crumbs=[("خانه", "/"), ("آثار", reverse("gallery:index")), (category.title, None)],
    )
    from apps.core.structured_data import collection_json_ld
    return render(request, "gallery/category.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"],
        "featured_project": __import__("apps.projects.models", fromlist=["Project"]).Project.objects.filter(featured=True, published=True).first(),
        "category": category, "items": items, "categories": public_categories(),
        "collection_ld": collection_json_ld(category, items, seo["canonical"]),
    })
