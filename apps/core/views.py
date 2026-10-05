from django.core.paginator import Paginator
from django.shortcuts import render
from django.template import TemplateDoesNotExist, loader

from .models import HomepageSection, ProcessStep, Statistic
from apps.projects.models import Project


SECTION_TEMPLATE_MAP = {
    HomepageSection.SectionType.HERO: "core/sections/hero.html",
    HomepageSection.SectionType.BRAND_INTRO: "core/sections/brand_intro.html",
    HomepageSection.SectionType.DIFFERENTIATOR: "core/sections/differentiator.html",
    HomepageSection.SectionType.FEATURED_PROJECTS: "core/sections/featured_projects.html",
    HomepageSection.SectionType.COMPANY_VIDEO: "core/sections/company_video.html",
    HomepageSection.SectionType.SERVICES: "core/sections/services.html",
    HomepageSection.SectionType.PRODUCT_HIGHLIGHT: "core/sections/product_highlight.html",
    HomepageSection.SectionType.STATISTICS: "core/sections/statistics.html",
    HomepageSection.SectionType.WORKSHOP: "core/sections/workshop.html",
    HomepageSection.SectionType.TEAM: "core/sections/team.html",
    HomepageSection.SectionType.GALLERY: "core/sections/gallery.html",
    HomepageSection.SectionType.CTA: "core/sections/cta.html",
}


def _stage_photos(project):
    """One real photo per project stage (design → build → install → result) for the homepage filmstrip."""
    labels = dict(project.images.model.Stage.choices)
    seen, photos = set(), []
    for img in project.images.filter(active=True).order_by("display_order"):
        if img.stage in seen:
            continue
        seen.add(img.stage)
        photos.append({"stage": img.stage, "label": labels.get(img.stage, ""), "image": img.image, "alt": img.alt_text or project.title})
    order = ["design", "build", "install", "result"]
    return sorted(photos, key=lambda p: order.index(p["stage"]) if p["stage"] in order else 9)


def home_view(request):
    sections = HomepageSection.objects.filter(is_visible=True, published=True).order_by("display_order")

    rendered_sections = []
    for section in sections:
        template_name = SECTION_TEMPLATE_MAP.get(section.section_type)
        if not template_name:
            continue
        extra_context = {}
        if section.section_type == HomepageSection.SectionType.HERO:
            extra_context["hero_project"] = Project.objects.filter(featured=True, published=True).first()
        if section.section_type == HomepageSection.SectionType.FEATURED_PROJECTS:
            featured = list(Project.objects.filter(featured=True, published=True).select_related("category")[:6])
            for project in featured:
                project.stage_photos = _stage_photos(project)
            extra_context["featured_projects"] = featured
        if section.section_type == HomepageSection.SectionType.STATISTICS:
            extra_context["statistics"] = Statistic.objects.filter(published=True)
        if section.section_type == HomepageSection.SectionType.DIFFERENTIATOR:
            extra_context["process_steps"] = ProcessStep.objects.filter(published=True)
        if section.section_type == HomepageSection.SectionType.WORKSHOP:
            from apps.company.models import WorkshopSection
            extra_context["workshop"] = WorkshopSection.objects.filter(published=True).order_by("display_order", "id").first()
        if section.section_type == HomepageSection.SectionType.PRODUCT_HIGHLIGHT:
            from apps.products.models import Product
            extra_context["product"] = Product.objects.filter(published=True).prefetch_related("features").first()
        if section.section_type == HomepageSection.SectionType.SERVICES:
            from apps.services.models import Service
            extra_context["services"] = Service.objects.filter(published=True)
        if section.section_type == HomepageSection.SectionType.GALLERY:
            from apps.gallery.views import public_categories
            extra_context["work_categories"] = public_categories()
        if section.section_type == HomepageSection.SectionType.TEAM:
            from apps.company.models import TeamMember
            extra_context["team_members"] = TeamMember.objects.filter(published=True)[:4]
        try:
            html = loader.render_to_string(template_name, {"section": section, **extra_context}, request=request)
        except TemplateDoesNotExist:
            continue
        rendered_sections.append(html)

    from apps.core.seo import build_seo
    ss = request.site_settings
    context = {"rendered_sections": rendered_sections, "seo": build_seo(
        request, title=(ss.default_seo_title if ss and ss.default_seo_title else "پرتو نور | طراحی، ساخت و اجرای المان‌های نوری و نورپردازی شهری"), brand=False,
        description=ss.default_seo_description if ss else "")}

    # Graceful-empty handling (spec requirement): a fresh install seeds
    # every HomepageSection with is_visible=False on purpose — no fake
    # content is ever shown to the public. But a totally blank page with
    # zero explanation looks like a bug to whoever opens it first. This
    # message is staff-only (never shown to an anonymous/public visitor)
    # and links straight to the admin screen that fixes it — it is
    # operational guidance, not homepage content, so it doesn't violate
    # the no-fake-content rule.
    if not rendered_sections and request.user.is_authenticated and request.user.is_staff:
        context["show_staff_empty_homepage_notice"] = True

    return render(request, "core/home.html", context)


def search_view(request):
    query = request.GET.get("q", "").strip()
    results = {"projects": [], "services": [], "articles": [], "products": [], "works": []}
    paginated = {}

    if query:
        from apps.services.models import Service
        from apps.articles.models import Article
        from apps.products.models import Product

        from django.db.models import Q
        from apps.gallery.models import GalleryItem

        querysets = {
            "projects": Project.objects.filter(published=True).filter(
                Q(title__icontains=query) | Q(short_description__icontains=query) | Q(full_description__icontains=query)
                | Q(city__icontains=query) | Q(design_concept__icontains=query)),
            "services": Service.objects.filter(published=True).filter(
                Q(title__icontains=query) | Q(short_description__icontains=query) | Q(full_description__icontains=query)),
            "articles": Article.objects.filter(published=True).filter(
                Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(content__icontains=query)),
            "products": Product.objects.filter(published=True).filter(
                Q(title__icontains=query) | Q(short_description__icontains=query) | Q(full_description__icontains=query)),
            "works": GalleryItem.objects.filter(is_visible=True, needs_review=False, category__isnull=False).filter(
                Q(title__icontains=query) | Q(caption__icontains=query) | Q(category__title__icontains=query)
            ).select_related("category"),
        }
        for key, qs in querysets.items():
            page_number = request.GET.get(f"{key}_page")
            paginator = Paginator(qs, 10)
            paginated[key] = paginator.get_page(page_number)
        results = paginated

    from apps.core.seo import build_seo
    seo = build_seo(request, title="جست‌وجو در سایت", description="جست‌وجو در پروژه‌ها، خدمات، مقالات و آثار پرتو نور.",
                    robots="noindex, follow", canonical_path="/search/", crumbs=[("خانه", "/"), ("جست‌وجو", None)])
    return render(request, "core/search.html", {"seo": seo, "breadcrumb_items": seo["breadcrumb_items"], "query": query, "results": results})
