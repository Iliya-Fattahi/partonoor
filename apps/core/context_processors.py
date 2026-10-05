from django.core.cache import cache
from django.db.models import Prefetch

from .models import Navigation, NavigationItem

NAV_CACHE_KEY = "navigation_context_v1"
NAV_CACHE_TTL = 60 * 15  # 15 min fallback — actual invalidation is immediate via signals (see signals.py)


def site_settings(request):
    from apps.core.structured_data import organization_json_ld

    settings_obj = getattr(request, "site_settings", None)
    def _hires(field, min_width):
        # A 32px favicon-sized logo looks blurry in the header; only use an uploaded
        # logo when it is big enough, otherwise templates fall back to the vector mark.
        try:
            return bool(field) and field.width >= min_width
        except Exception:
            return False

    context = {"site_settings": settings_obj}
    if settings_obj is not None:
        context["logo_full_ok"] = _hires(settings_obj.logo_full, 160)
        context["logo_symbol_ok"] = _hires(settings_obj.logo_symbol, 96)
    if settings_obj is not None:
        context["organization_json_ld"] = organization_json_ld(settings_obj)
    return context


def seo_defaults(request):
    """Fallback `seo` so a page that forgets to build one still gets a correct canonical / title."""
    from apps.core.seo import build_seo
    ss = getattr(request, "site_settings", None)
    title = (ss.default_seo_title or ss.company_name_fa) if ss else "پرتو نور"
    return {"seo": build_seo(request, title=title, brand=False)}


def navigation(request):
    cached = cache.get(NAV_CACHE_KEY)
    if cached is not None:
        return cached

    # NOTE: calling .filter() on a manager that was already loaded via
    # prefetch_related() bypasses the prefetch cache and issues a fresh
    # query — a subtle, easy-to-miss N+1 source. Using Prefetch with the
    # filter baked into the queryset avoids that: the filtered result is
    # what actually gets cached by prefetch_related in the first place.
    children_qs = NavigationItem.objects.filter(active=True)
    top_level_qs = NavigationItem.objects.filter(parent__isnull=True, active=True).prefetch_related(
        Prefetch("children", queryset=children_qs)
    )

    main_menu = (
        Navigation.objects.filter(slot="main")
        .prefetch_related(Prefetch("items", queryset=top_level_qs))
        .first()
    )
    footer_menu = Navigation.objects.filter(slot="footer").prefetch_related(
        Prefetch("items", queryset=NavigationItem.objects.filter(active=True))
    ).first()

    context = {
        "main_menu_items": list(main_menu.items.all()) if main_menu else [],
        "footer_menu_items": list(footer_menu.items.all()) if footer_menu else [],
    }
    cache.set(NAV_CACHE_KEY, context, NAV_CACHE_TTL)
    return context
