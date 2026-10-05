from django.urls import reverse
from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.seo import build_seo
from apps.core.structured_data import product_json_ld

from .forms import ProductOrderForm
from .models import Product


def product_list(request):
    products = Product.objects.filter(published=True)
    seo = build_seo(
        request,
        title="ریسه نوری؛ ثبت سفارش ریسه عرض خیابانی",
        description="ریسه نوری اختصاصی پرتو نور: کیفیت هم‌سطح نمونه‌های خارجی، قیمت مناسب‌تر و مقاومت بالا در برابر شرایط آب‌وهوایی؛ ثبت سفارش آنلاین.",
        crumbs=[("خانه", "/"), ("ریسه نوری", None)],
    )
    return render(request, "products/product_list.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"], "products": products})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related("features", "images", "videos"), slug=slug, published=True,
    )
    seo = build_seo(
        request,
        title=product.seo_title or f"{product.title}؛ سفارش ریسه نوری عرض خیابانی",
        description=product.seo_description or product.short_description,
        image=product.seo_image or product.main_image, og_type="website",
        crumbs=[("خانه", "/"), ("ریسه نوری", reverse("products:list")), (product.title, None)],
    )
    breadcrumb_items = seo["breadcrumb_items"]
    form = ProductOrderForm()
    if request.method == "POST":
        form = ProductOrderForm(request.POST)
        ip = request.META.get("REMOTE_ADDR", "x")
        key = f"order-rate:{ip}"
        if (cache.get(key) or 0) >= 5:
            messages.error(request, "درخواست‌های زیادی ارسال شده است. کمی بعد دوباره تلاش کنید.")
        elif form.is_valid():
            order = form.save(commit=False)
            order.product = product
            order.save()
            cache.set(key, (cache.get(key) or 0) + 1, 3600)
            messages.success(request, "سفارش شما ثبت شد. کارشناسان ما به‌زودی برای هماهنگی نهایی با شما تماس می‌گیرند.")
            return redirect(product.get_absolute_url() + "#order")
    return render(request, "products/product_detail.html", {
        "product": product,
        "order_form": form,
        "json_ld": product_json_ld(product, request.site_settings),
        "seo": seo,
        "breadcrumb_items": breadcrumb_items,
    })
