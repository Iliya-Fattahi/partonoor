from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.core.seo import build_seo, clean_text
from apps.core.structured_data import service_json_ld

from .models import Service


def service_list(request):
    services = Service.objects.filter(published=True)
    seo = build_seo(
        request,
        title="خدمات و راهکارهای نورپردازی شهری؛ از بازدید تا پشتیبانی",
        description="خدمات پرتو نور: بازدید، شناخت فرهنگ و داستان شهر، مطالعه‌ی معماری فضا، طراحی اختصاصی، ساخت، نصب و پشتیبانی المان‌های نوری.",
        crumbs=[("خانه", "/"), ("خدمات", None)],
    )
    return render(request, "services/service_list.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"], "services": services})


def service_detail(request, slug):
    service = get_object_or_404(Service.objects.prefetch_related("gallery_images"), slug=slug, published=True)
    desc = service.seo_description or clean_text(
        f"{service.short_description} این مرحله بخشی از فرایند طراحی و اجرای اختصاصی المان نوری شهری در پرتو نور است.")
    seo = build_seo(
        request,
        title=service.seo_title or (f"{service.title}؛ خدمات نورپردازی شهری" if len(service.title) <= 28 else service.title),
        description=desc, image=service.seo_image,
        crumbs=[("خانه", "/"), ("خدمات", reverse("services:list")), (service.title, None)],
    )
    return render(request, "services/service_detail.html", {
        "service": service, "seo": seo,
        "other_services": Service.objects.filter(published=True).exclude(pk=service.pk), "service_ld": service_json_ld(service, request.site_settings),
        "breadcrumb_items": seo["breadcrumb_items"],
    })
