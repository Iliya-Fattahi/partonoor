from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_ico_file, validate_image_file, validate_svg_file, validate_video_file


class SEOFields(models.Model):
    """Abstract base — every public content type gets consistent SEO controls."""

    seo_title = models.CharField(
        _("عنوان سئو"), max_length=70, blank=True,
        help_text=_("در صورت خالی بودن، از عنوان اصلی استفاده می‌شود."),
    )
    seo_description = models.CharField(
        _("توضیحات متا"), max_length=160, blank=True,
    )
    seo_image = models.ImageField(
        _("تصویر اشتراک‌گذاری (OG)"), upload_to="seo/", blank=True, null=True,
        validators=[validate_image_file],
    )

    class Meta:
        abstract = True


class OrderedPublishable(models.Model):
    """Abstract base for anything the client reorders/publishes from the admin."""

    display_order = models.PositiveIntegerField(_("ترتیب نمایش"), default=0)
    published = models.BooleanField(_("منتشر شده"), default=True)
    created_at = models.DateTimeField(_("تاریخ ایجاد"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاریخ بروزرسانی"), auto_now=True)

    class Meta:
        abstract = True
        ordering = ["display_order", "-created_at"]


class SingletonModel(models.Model):
    """Ensures only one row can ever exist (e.g. SiteSettings)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # singleton rows are never deletable from the admin

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(SingletonModel):
    """Everything global and brand-level, editable without a developer."""

    company_name_fa = models.CharField(_("نام شرکت (فارسی)"), max_length=255, default="پرتو نور")
    company_name_en = models.CharField(_("نام شرکت (انگلیسی)"), max_length=255, blank=True, default="", help_text=_("اختیاری؛ زیر نام فارسی در هدر نمایش داده می‌شود."))
    slogan = models.CharField(
        _("شعار"), max_length=255, blank=True,
        default="طراحی، ساخت و اجرای المان‌های نوری و نورپردازی شهری",
    )

    # Brand assets — see spec section 4: symbol must never be regenerated
    logo_full = models.ImageField(_("لوگوی کامل"), upload_to="brand/", blank=True, null=True, validators=[validate_image_file])
    logo_symbol = models.ImageField(
        _("نماد/آیکون برند"), upload_to="brand/", blank=True, null=True,
        help_text=_("این نماد در فاویکون، هدر موبایل و صفحه بارگذاری استفاده می‌شود."),
        validators=[validate_image_file],
    )
    logo_light = models.ImageField(_("لوگو نسخه روشن"), upload_to="brand/", blank=True, null=True, validators=[validate_image_file])
    logo_dark = models.ImageField(_("لوگو نسخه تیره"), upload_to="brand/", blank=True, null=True, validators=[validate_image_file])
    favicon_ico = models.FileField(_("فاویکون (.ico)"), upload_to="brand/", blank=True, null=True, validators=[validate_ico_file])
    favicon_svg = models.FileField(_("فاویکون (SVG)"), upload_to="brand/", blank=True, null=True, validators=[validate_svg_file])

    phone = models.CharField(_("شماره تماس"), max_length=32, blank=True, help_text=_("مثال: 09151234567 — در هدر، فوتر، صفحه‌ی تماس و دکمه‌ی تماس موبایل نمایش داده می‌شود."))
    show_whatsapp = models.BooleanField(_("نمایش واتس‌اپ"), default=True, help_text=_("پیوند واتس‌اپ از همان «شماره تماس» ساخته می‌شود."))
    show_telegram = models.BooleanField(_("نمایش تلگرام"), default=True, help_text=_("پیوند تلگرام از همان «شماره تماس» ساخته می‌شود."))
    instagram_url = models.URLField(_("اینستاگرام"), blank=True, help_text=_("آدرس کامل صفحه، مثلاً https://www.instagram.com/نام_کاربری/"))

    footer_text = models.TextField(_("متن فوتر"), blank=True)
    copyright_text = models.CharField(_("متن کپی‌رایت"), max_length=255, blank=True)

    default_seo_title = models.CharField(_("عنوان پیش‌فرض سئو"), max_length=70, blank=True)
    default_seo_description = models.CharField(_("توضیحات پیش‌فرض سئو"), max_length=160, blank=True)
    default_og_image = models.ImageField(
        _("تصویر پیش‌فرض اشتراک‌گذاری"), upload_to="seo/", blank=True, null=True,
        validators=[validate_image_file],
    )

    maintenance_mode = models.BooleanField(
        _("حالت تعمیرات فعال باشد"), default=False,
        help_text=_("با فعال‌کردن آن، بازدیدکنندگان فقط «صفحه‌ی تعمیرات» را می‌بینند. پنل مدیریت و مدیر واردشده سایت را عادی می‌بینند."),
    )
    maintenance_title = models.CharField(_("عنوان صفحه‌ی تعمیرات"), max_length=150, blank=True, default="سایت در حال به‌روزرسانی است")
    maintenance_message = models.TextField(
        _("متن صفحه‌ی تعمیرات"), blank=True,
        default="در حال انجام کارهای فنی و به‌روزرسانی هستیم و به‌زودی برمی‌گردیم. از شکیبایی شما سپاسگزاریم.",
    )

    class Meta:
        verbose_name = _("تنظیمات سایت")
        verbose_name_plural = _("تنظیمات سایت")

    def __str__(self):
        return str(self.company_name_fa)

    @property
    def phone_international(self):
        """Digits only, Iranian mobile in international form (989…), or '' if the number is unusable."""
        digits = "".join(ch for ch in str(self.phone).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")) if ch.isdigit())
        if digits.startswith("0098"):
            digits = digits[2:]
        if digits.startswith("0"):
            digits = "98" + digits[1:]
        return digits if len(digits) >= 10 else ""

    @property
    def whatsapp_link(self):
        return f"https://wa.me/{self.phone_international}" if self.show_whatsapp and self.phone_international else ""

    @property
    def telegram_link(self):
        return f"https://t.me/+{self.phone_international}" if self.show_telegram and self.phone_international else ""


class Navigation(models.Model):
    """A named menu (e.g. 'main', 'footer') containing NavigationItems."""

    SLOT_CHOICES = [("main", _("منوی اصلی")), ("footer", _("منوی فوتر"))]

    slot = models.CharField(_("محل نمایش"), max_length=20, choices=SLOT_CHOICES, unique=True)

    class Meta:
        verbose_name = _("منو")
        verbose_name_plural = _("منوها")

    def __str__(self):
        return self.get_slot_display()


class NavigationItem(models.Model):
    navigation = models.ForeignKey(Navigation, on_delete=models.CASCADE, related_name="items", verbose_name=_("منو"))
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True, blank=True,
        verbose_name=_("زیرمجموعه از"),
    )
    title = models.CharField(_("عنوان"), max_length=100)
    url = models.CharField(
        _("آدرس"), max_length=255, blank=True,
        help_text=_("مسیر داخلی (مثلا /projects/) یا آدرس کامل خارجی."),
    )
    is_external = models.BooleanField(_("لینک خارجی"), default=False)
    open_in_new_tab = models.BooleanField(_("باز شدن در تب جدید"), default=False)
    display_order = models.PositiveIntegerField(_("ترتیب نمایش"), default=0)
    active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("آیتم منو")
        verbose_name_plural = _("آیتم‌های منو")
        ordering = ["display_order"]

    def __str__(self):
        return self.title


class Statistic(OrderedPublishable):
    """Homepage stat counters — number stays free-text so the client isn't forced into ints only."""

    label = models.CharField(_("عنوان"), max_length=100)
    value = models.CharField(_("مقدار"), max_length=50, help_text=_("مثلا 120+ یا 8 سال"))
    icon = models.CharField(_("آیکون (اختیاری)"), max_length=50, blank=True)

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("آمار")
        verbose_name_plural = _("آمارها")

    def __str__(self):
        return f"{self.label}: {self.value}"


class ProcessStep(OrderedPublishable):
    """
    The company's own stated collaboration process (spec section 9: "از
    ایده تا اجرا" / "فرآیند همکاری") — e.g. دریافت نیاز، مشاوره، بررسی
    محل، ایده‌پردازی، طراحی، تأیید طرح، ساخت، نورپردازی، نصب و اجرا،
    تحویل. This used to be hardcoded literal <li> text inside
    templates/core/sections/differentiator.html — a real content
    hardcode bug, since these are business content (the company's actual
    workflow), not structural markup, and must be admin-editable per
    spec section 17.
    """

    title = models.CharField(_("عنوان مرحله"), max_length=100)
    description = models.CharField(_("توضیح کوتاه (اختیاری)"), max_length=200, blank=True)

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("مرحله فرآیند همکاری")
        verbose_name_plural = _("مراحل فرآیند همکاری")

    def __str__(self):
        return self.title


class HomepageSection(OrderedPublishable):
    """
    A single ordered/toggleable block on the homepage. Content is generic so the
    dev never has to hardcode homepage HTML into templates — the client edits
    everything below through the admin.
    """

    class SectionType(models.TextChoices):
        HERO = "hero", _("هیرو")
        BRAND_INTRO = "brand_intro", _("معرفی برند")
        DIFFERENTIATOR = "differentiator", _("تفاوت پرتو نور")
        FEATURED_PROJECTS = "featured_projects", _("پروژه‌های منتخب")
        COMPANY_VIDEO = "company_video", _("ویدیوی معرفی شرکت")
        SERVICES = "services", _("خدمات")
        PRODUCT_HIGHLIGHT = "product_highlight", _("محصول ویژه (ریسه نوری)")
        STATISTICS = "statistics", _("آمار")
        WORKSHOP = "workshop", _("کارگاه/تیم")
        TEAM = "team", _("تیم")
        GALLERY = "gallery", _("گالری")
        CTA = "cta", _("دعوت به اقدام")

    section_type = models.CharField(_("نوع بخش"), max_length=30, choices=SectionType.choices, unique=True)
    kicker = models.CharField(_("برچسب کوچک بالای عنوان"), max_length=100, blank=True)
    title = models.CharField(_("عنوان"), max_length=255, blank=True)
    subtitle = models.TextField(_("زیرعنوان / توضیح"), blank=True)

    image = models.ImageField(_("تصویر"), upload_to="homepage/", blank=True, null=True, validators=[validate_image_file])
    video = models.FileField(_("ویدیو"), upload_to="homepage/videos/", blank=True, null=True, validators=[validate_video_file])
    video_poster = models.ImageField(_("پوستر ویدیو"), upload_to="homepage/", blank=True, null=True, validators=[validate_image_file])

    cta_label = models.CharField(_("متن دکمه"), max_length=100, blank=True)
    cta_url = models.CharField(_("آدرس دکمه"), max_length=255, blank=True)

    is_visible = models.BooleanField(_("نمایش در صفحه اصلی"), default=True)

    class Meta(OrderedPublishable.Meta):
        verbose_name = _("بخش صفحه اصلی")
        verbose_name_plural = _("بخش‌های صفحه اصلی")

    def __str__(self):
        return self.get_section_type_display()

    def clean(self):
        if self.section_type == self.SectionType.COMPANY_VIDEO and not self.video:
            raise ValidationError(_("برای بخش ویدیوی معرفی شرکت، فایل ویدیو الزامی است."))
