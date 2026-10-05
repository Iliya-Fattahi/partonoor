from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.core.seo import build_seo
from apps.core.structured_data import project_json_ld

from .models import Project, ProjectCategory


def project_list(request):
    projects = (
        Project.objects.filter(published=True)
        .select_related("category")
        .prefetch_related("images")
    )

    category_slug = request.GET.get("category")
    categories = ProjectCategory.objects.filter(published=True)
    active_category = None
    if category_slug:
        active_category = get_object_or_404(ProjectCategory, slug=category_slug, published=True)
        projects = projects.filter(category=active_category)

    paginator = Paginator(projects, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    page_no = page_obj.number
    seo = build_seo(
        request,
        title="پروژه‌ها؛ مطالعه‌ی موردی طراحی و اجرای المان نوری شهری",
        description="مطالعه‌ی موردی پروژه‌های پرتو نور: از طراحی و ساخت تا نصب و اجرای المان‌های نوری شهری، از جمله پروژه‌ی هفت‌خان رستم.",
        robots="noindex, follow" if active_category else "",
        canonical_path=reverse("projects:list") if active_category else None,
        page=page_no, crumbs=[("خانه", "/"), ("پروژه‌ها", None)],
    )
    return render(request, "projects/project_list.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"],
        "page_obj": page_obj,
        "categories": categories,
        "active_category": active_category,
    })


def project_detail(request, slug):
    project = get_object_or_404(
        Project.objects.select_related("category").prefetch_related("images", "videos"),
        slug=slug, published=True,
    )
    related_projects = (
        Project.objects.filter(category=project.category, published=True)
        .exclude(pk=project.pk)
        .select_related("category")[:3]
    )

    works = project.gallery_items.filter(is_visible=True, category__published=True).select_related("category")
    first_work = works.first()
    works_category = first_work.category if first_work else None
    related_works = list(works[:4])

    seo = build_seo(
        request,
        title=project.seo_title or f"{project.title}؛ مطالعه‌ی موردی طراحی، ساخت و اجرا",
        description=project.seo_description or project.short_description,
        image=project.seo_image or project.cover_image, og_type="article",
        modified=project.updated_at,
        crumbs=[("خانه", "/"), ("پروژه‌ها", reverse("projects:list")), (project.title, None)],
    )
    breadcrumb_items = seo["breadcrumb_items"]

    stages = [
        ("design", "طراحی", project.design_concept),
        ("build", "ساخت", project.manufacturing_notes),
        ("install", "نصب و اجرا", project.execution_notes),
        ("result", "نتیجه‌ی نهایی", ""),
    ]
    used = {img.stage for img in project.images.all() if img.active}
    stages = [row for row in stages if row[0] in used]
    stage_groups = []
    for key, _title, _text in stages:
        imgs = [i for i in project.images.all() if i.stage == key and i.active]
        stage_groups.append({"key": key, "lead": imgs[0] if imgs else None, "rest": imgs[1:]})
    return render(request, "projects/project_detail.html", {
        "stage_groups": stage_groups,
        "stages": stages,
        "project": project,
        "related_projects": related_projects,
        "works_category": works_category,
        "related_works": related_works,
        "json_ld": project_json_ld(project, request.site_settings, [i for g in stage_groups for i in ([g["lead"]] if g["lead"] else []) + g["rest"]]),
        "seo": seo,
        "breadcrumb_items": breadcrumb_items,
    })
