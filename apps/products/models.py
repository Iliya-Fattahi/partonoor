from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrderedPublishable, SEOFields
from apps.core.validators import validate_image_file, validate_video_file


class Product(OrderedPublishable, SEOFields):
    """
    The lighting string (or any future product). Deliberately has NO price,
    cart, or checkout fields — spec section 17/69: showcase only, contact-to-order.
    """

    title = models.CharField(_("عنوان"), max_length=200)
    slug = models.SlugField(_("اسلاگ"), max_length=220, unique=True, blank=True)
    short_description = models.CharField(_("توضیح کوتاه"), max_length=300)
    full_description = models.TextField(_("توضیح کامل"))
    main_image = models.ImageField(_("تصویر اصلی"), upload_to="products/", validators=[validate_image_file])

    order_cta_label = models.CharField(_("متن دکمه سفارش"), max_length=100, default="تماس بگیرید و سفارش دهید")
    # Deliberately no order_cta_url field pointing at a payment gateway — the
    # template always resolves the contact channel from SiteSettings.

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("محصول")
        verbose_name_plural = _("محصولات")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})


class ProductFeature(models.Model):
    """A single confirmed differentiator claim — no invented specs (spec section 18)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="features", verbose_name=_("محصول"))
    title = models.CharField(_("عنوان ویژگی"), max_length=200)
    description = models.TextField(_("توضیح"), blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("ویژگی محصول")
        verbose_name_plural = _("ویژگی‌های محصول")
        ordering = ["display_order"]

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name=_("محصول"))
    image = models.ImageField(_("تصویر"), upload_to="products/gallery/", validators=[validate_image_file])
    alt_text = models.CharField(_("متن جایگزین"), max_length=200, blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("تصویر محصول")
        verbose_name_plural = _("تصاویر محصول")
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.product.title} — image {self.pk}"


class ProductVideo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="videos", verbose_name=_("محصول"))
    video = models.FileField(_("فایل ویدیو"), upload_to="products/videos/", validators=[validate_video_file])
    poster = models.ImageField(_("پوستر"), upload_to="products/videos/posters/", validators=[validate_image_file])
    title = models.CharField(_("عنوان"), max_length=200, blank=True)
    display_order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("ویدیوی محصول")
        verbose_name_plural = _("ویدیوهای محصول")
        ordering = ["display_order"]

    def __str__(self):
        return self.title or f"{self.product.title} — video {self.pk}"



class ProductOrder(models.Model):
    """سفارش ریسه — ثبت در دیتابیس و نمایش در پنل مدیریت. بدون پرداخت آنلاین."""

    class Status(models.TextChoices):
        NEW = "new", _("جدید")
        CONTACTED = "contacted", _("تماس گرفته شد")
        DONE = "done", _("نهایی شد")
        CANCELLED = "cancelled", _("لغو شد")

    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders", verbose_name=_("محصول"))
    name = models.CharField(_("نام و نام خانوادگی"), max_length=150)
    company = models.CharField(_("شرکت / سازمان"), max_length=150, blank=True)
    phone = models.CharField(_("شماره تماس"), max_length=30)
    city = models.CharField(_("شهر"), max_length=100)
    quantity = models.CharField(_("مقدار موردنیاز"), max_length=100, help_text=_("مثلاً ۲۰۰ متر"))
    model_type = models.CharField(_("نوع / مدل / رنگ"), max_length=150, blank=True)
    usage = models.CharField(_("محل یا کاربرد"), max_length=200, blank=True)
    message = models.TextField(_("توضیحات"), blank=True)
    status = models.CharField(_("وضعیت"), max_length=12, choices=Status.choices, default=Status.NEW)
    admin_note = models.TextField(_("یادداشت داخلی"), blank=True)
    created_at = models.DateTimeField(_("زمان ثبت"), auto_now_add=True)

    class Meta:
        verbose_name = _("سفارش ریسه")
        verbose_name_plural = _("سفارش‌های ریسه")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.quantity}"
