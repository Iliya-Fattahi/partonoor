from django.shortcuts import render

from apps.core.seo import build_seo

from .models import AboutSection, TeamMember, WorkshopSection


def about_view(request):
    seo = build_seo(
        request,
        title="درباره‌ی پرتو نور و فلسفه‌ی «نور مسئول»",
        description="فلسفه‌ی پرتو نور: نور مسئول، نگاه به شهر و انرژی، و رویکرد طراحی اختصاصی و ساخت المان‌های نوری شهری.",
        crumbs=[("خانه", "/"), ("درباره‌ی ما", None)],
    )
    return render(request, "company/about.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"],
        "sections": AboutSection.objects.filter(published=True),
        "team": TeamMember.objects.filter(published=True),
    })


def workshop_view(request):
    seo = build_seo(
        request,
        title="کارگاه ساخت المان نوری",
        description="کارگاه پرتو نور: جایی که طرح‌های اختصاصی المان نوری، لوستر شهری و ریسه ساخته و پیش از نصب بررسی می‌شوند.",
        crumbs=[("خانه", "/"), ("کارگاه", None)],
    )
    return render(request, "company/workshop.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"],
        "blocks": WorkshopSection.objects.filter(published=True),
    })
