"""
Seeds the REAL client-provided material as normal, fully editable database content:
work categories (from the client's handwritten sheet), the curated photos, the
Haft Khan Rostam case study, the ریسه product, services, the two real articles
(text extracted from the client's screenshots), navigation and homepage sections.

Nothing here is hard-coded in templates; everything is editable/deletable in the admin.
No invented facts: city / year / client of the projects, phone, e-mail, address are left
empty for the client to fill in.

Idempotent by default (skips what already exists). Flags:
    --reset-works     delete every existing work (GalleryItem) and re-seed from manifest
    --reset-project   delete and re-create the Haft Khan project
    --reset-nav       rebuild main/footer menus
    --reset-home      overwrite homepage section content + order

Usage (after migrate):  python manage.py seed_real_media
"""
import json
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.articles.models import Article, ArticleCategory
from apps.core.models import HomepageSection, Navigation, NavigationItem, ProcessStep, SiteSettings
from apps.gallery.models import GalleryItem, WorkCategory
from apps.products.models import Product, ProductFeature, ProductImage
from apps.projects.models import Project, ProjectCategory, ProjectImage
from apps.services.models import Service

ASSETS = Path(__file__).resolve().parents[4] / "seed_assets"
WORKS = ASSETS / "works"

# Order and names exactly as written on the client's sheet under «آثار».
CATEGORIES = [
    "المان‌های نوری زمینی و مناسبتی",
    "المان‌های نوری داستانی",
    "لوسترهای نوری شهری",
    "ریسه‌های نوری عرض خیابانی",
    "نورپردازی دینامیک",
    "محصول اختصاصی ریسه نوری",
    "کاتالوگ",
]

SERVICES = [  # titles from the client's sheet «خدمات و راهکارها»
    ("بازدید", "آغاز هر پروژه با بازدید میدانی از محل و شناخت شرایط واقعی فضا.", "proc-team-02"),
    ("شناخت فرهنگ و داستان‌ها جهت نورپردازی", "نور خوب از داستان شهر می‌آید؛ فرهنگ، تاریخ و روایت‌های محلی پایه‌ی طراحی ما هستند.", "story-06"),
    ("مطالعه معماری فضا و مکان", "بررسی معماری، مقیاس و مسیرهای دید تا نور با فضا هم‌سخن باشد.", "luster-03"),
    ("طراحی اختصاصی", "طراحی المان و راهکار نوری متناسب با شهر، محیط و مفهوم پروژه.", "proc-design-02"),
    ("ساخت", "ساخت المان‌های نوری طراحی‌شده.", "proc-build-04"),
    ("نصب", "نصب و اجرای پروژه در محل.", "proc-install-03"),
    ("پشتیبانی", "همراهی پس از اجرا برای نگهداری و رفع اشکال.", "proc-team-01"),
]

RISHEH_FEATURES = [  # advantages exactly as stated by the client
    ("کیفیت هم‌سطح محصولات خارجی", "ساخت با معیارهای کیفی همتراز نمونه‌های وارداتی."),
    ("قیمت مناسب‌تر", "تولید داخل و قیمت رقابتی‌تر نسبت به نمونه‌های خارجی."),
    ("مقاومت بالا در برابر شرایط آب‌وهوایی", "طراحی‌شده برای فضای باز و شرایط جوی سخت."),
    ("کیفیت نور بالا", "نور روشن، یکنواخت و شفاف."),
    ("قابلیت استفاده در پروژه‌های مختلف", "مناسب خیابان و میدان، مناسبت‌ها، فضاهای تجاری و مجموعه‌ها."),
    ("ارائه متناسب با نیاز پروژه", "مقدار، رنگ و نوع اجرا بر اساس نیاز هر پروژه."),
]


PROCESS = [  # the company's real workflow, as defined by the client
    ("نیازسنجی", "شنیدن نیاز و هدف شهر یا مجموعه."),
    ("بازدید و شناخت فضا", "بازدید میدانی و شناخت معماری، مکان، فرهنگ و داستان محل."),
    ("طراحی اختصاصی", "طراحی المان یا راهکار نوری متناسب با همان پروژه."),
    ("بررسی و مهندسی", "بررسی فنی و مهندسی طرح پیش از ساخت."),
    ("ساخت", "ساخت المان‌ها."),
    ("نورپردازی", "اجرای نور و تنظیم آن روی المان."),
    ("نصب و اجرا", "نصب و راه‌اندازی در محل پروژه."),
    ("پشتیبانی", "همراهی پس از اجرا."),
]


class Command(BaseCommand):
    help = "Seed real client content (categories, works, project, product, services, articles, menus, homepage)."

    def add_arguments(self, parser):
        for f in ("works", "project", "nav", "home"):
            parser.add_argument(f"--reset-{f}", action="store_true")

    # ---------------------------------------------------------------- helpers
    def _attach(self, field, path):
        path = Path(path)
        with open(path, "rb") as fh:
            field.save(path.name, File(fh), save=False)

    def _img(self, key):
        return WORKS / f"{key}.jpg"

    def handle(self, *args, **o):
        if not WORKS.exists():
            self.stderr.write(self.style.ERROR(f"{WORKS} not found."))
            return
        self.manifest = json.loads((WORKS / "manifest.json").read_text(encoding="utf-8"))
        self._settings()
        self._categories()
        self._works(o["reset_works"])
        project = self._project(o["reset_project"])
        product = self._product()
        self._services()
        self._articles()
        self._seo_polish()
        self._process_steps()
        self._navigation(o["reset_nav"])
        self._homepage(o["reset_home"])
        from django.core.management import call_command
        call_command("optimize_images")
        self.stdout.write(self.style.SUCCESS("Done."))

    # --------------------------------------------------------------- settings
    def _settings(self):
        s = SiteSettings.load()
        changed = False
        if not s.favicon_ico and (ASSETS / "favicon.ico").exists():
            self._attach(s.favicon_ico, ASSETS / "favicon.ico"); changed = True
        # logo_* are required fields; the only logo supplied so far is a 32px icon. Templates ignore
        # logos smaller than 160px/96px and show a vector mark instead — replace with the real logo.
        for name in ("logo_symbol", "logo_full"):
            if not getattr(s, name) and (ASSETS / "logo_symbol.png").exists():
                self._attach(getattr(s, name), ASSETS / "logo_symbol.png"); changed = True
        # Contact details supplied by the client (the only ones they have; no address/e-mail exist).
        if not s.phone:
            s.phone = "09156249754"; changed = True
        if not s.instagram_url:
            s.instagram_url = "https://www.instagram.com/partonoor.co/"; changed = True
        if not s.slogan:
            s.slogan = "طراحی، ساخت و اجرای راهکارهای نوری اختصاصی شهری"; changed = True
        if not s.default_seo_title:
            s.default_seo_title = "پرتو نور | طراحی، ساخت و اجرای المان‌های نوری و نورپردازی شهری"; changed = True
        if not s.default_seo_description:
            s.default_seo_description = "پرتو نور: طراحی و ساخت اختصاصی المان نوری داستانی، لوستر نوری شهری، ریسه نوری عرض خیابانی و نورپردازی دینامیک؛ از نیازسنجی تا نصب و پشتیبانی."; changed = True
        if changed:
            s.save()

    # ------------------------------------------------------------- categories
    def _categories(self):
        for i, title in enumerate(CATEGORIES):
            WorkCategory.objects.get_or_create(title=title, defaults={"display_order": i, "published": True})

    # ------------------------------------------------------------------ works
    def _works(self, reset):
        if reset:
            GalleryItem.objects.all().delete()
        if GalleryItem.objects.exists():
            self.stdout.write("Works already exist — skipping (use --reset-works to re-seed).")
            return
        cats = {c.title: c for c in WorkCategory.objects.all()}
        n = 0
        for i, m in enumerate(self.manifest):
            if m["role"] not in ("hero", ""):   # process photos belong to the project case study
                continue
            item = GalleryItem(
                media_type="image", title=m["title"], caption=m["caption"], alt_text=m["title"],
                category=cats.get(m["category"]), display_order=i, is_visible=True,
                needs_review=not m["visible"],
            )
            self._attach(item.image, self._img(m["id"]))
            item.save(); n += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {n} works ({GalleryItem.objects.filter(needs_review=True).count()} flagged «در انتظار تأیید»)."))

    # ---------------------------------------------------------------- project
    def _project(self, reset):
        slug = "haft-khan-rostam"
        if reset:
            Project.objects.filter(slug=slug).delete()
        p = Project.objects.filter(slug=slug).first()
        if p:
            return p
        cat, _ = ProjectCategory.objects.get_or_create(title="المان نوری داستانی")
        p = Project(
            title="هفت‌خان رستم", slug=slug, category=cat, featured=True, published=True, display_order=0,
            short_description="المان‌های نوری داستانی که روایت شاهنامه‌ای هفت‌خان رستم را به خیابان‌های شهر می‌آورند.",
            full_description=(
                "«هفت‌خان رستم» مجموعه‌ای از المان‌های نوری داستانی است که صحنه‌های شاهنامه را با خطوط نور و خوشنویسی روی خیابان‌های شهر روایت می‌کند.\n\n"
                "این پروژه در تمام مراحل، از طراحی نقش و ساخت المان‌ها تا نصب شبانه روی خیابان، توسط تیم پرتو نور انجام شده است."
            ),
        )
        self._attach(p.cover_image, self._img("story-01"))
        p.save()
        stage_of = {"design": "design", "build": "build", "install": "install", "team": "install", "": "result", "hero": "result"}
        order = 0
        for m in self.manifest:
            in_story = m["category"] == "المان‌های نوری داستانی"
            is_proc = m["id"].startswith("proc-")
            if not (in_story or is_proc) or not m["visible"]:
                continue
            img = ProjectImage(project=p, title=m["title"], alt_text=m["title"] or p.title, stage=stage_of[m["role"]], display_order=order, active=True)
            self._attach(img.image, self._img(m["id"])); img.save(); order += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded project «هفت‌خان رستم» with {order} staged photos."))
        return p

    # ---------------------------------------------------------------- product
    def _product(self):
        prod = Product.objects.filter(slug="risheh").first()
        if prod:
            return prod
        prod = Product(
            title="ریسه نوری پرتو نور", slug="risheh", published=True, display_order=0,
            order_cta_label="ثبت سفارش ریسه",
            short_description="ریسه نوری اختصاصی با کیفیت هم‌سطح نمونه‌های خارجی، قیمت مناسب‌تر و مقاومت بالا در برابر شرایط آب‌وهوایی.",
            full_description=(
                "ریسه‌ی پرتو نور محصولی است که خودمان تولید می‌کنیم و برای پروژه‌های مختلف قابل سفارش است.\n\n"
                "کیفیت نور بالا، مقاومت در برابر شرایط آب‌وهوایی و امکان ارائه متناسب با نیاز هر پروژه، آن را برای اجرا در خیابان، میدان و فضاهای تجاری مناسب می‌کند."
            ),
        )
        self._attach(prod.main_image, self._img("garland-01"))
        prod.save()
        for i, (t, d) in enumerate(RISHEH_FEATURES):
            ProductFeature.objects.create(product=prod, title=t, description=d, display_order=i)
        for i, key in enumerate(("garland-02", "garland-03", "garland-04")):
            pi = ProductImage(product=prod, alt_text="ریسه نوری پرتو نور", display_order=i)
            self._attach(pi.image, self._img(key)); pi.save()
        self.stdout.write(self.style.SUCCESS("Seeded product «ریسه»."))
        return prod

    # --------------------------------------------------------------- services
    def _services(self):
        for i, (title, desc, img) in enumerate(SERVICES):
            if Service.objects.filter(title=title).exists():
                continue
            s = Service(title=title, short_description=desc, full_description=desc, published=True, display_order=i)
            self._attach(s.main_image, self._img(img)); s.save()

    # --------------------------------------------------------------- articles
    def _articles(self):
        data = json.loads((ASSETS / "articles" / "articles.json").read_text(encoding="utf-8"))
        cats = {}
        for i, t in enumerate(["مقالات", "ایده‌های نورپردازی", "متریال و تکنولوژی", "اخبار و رویدادها"]):
            cats[t], _ = ArticleCategory.objects.get_or_create(title=t, defaults={"display_order": i})
        covers = ["luster-01", "luster-05"]
        figs = {"article1_fig1.jpg": ASSETS / "articles" / "article1_fig1.jpg", "article2_fig1.jpg": ASSETS / "articles" / "article2_fig1.jpg"}
        for art, cover in zip(data, covers):
            if Article.objects.filter(title=art["title"]).exists():
                continue
            html = art["body_html"]
            for name, src in figs.items():
                if f'src="{name}"' in html:
                    with open(src, "rb") as fh:
                        saved = default_storage.save(f"articles/figures/{name}", File(fh))
                    html = html.replace(f'src="{name}"', f'src="{default_storage.url(saved)}"')
            html = self._wrap_abstract(html)
            plain = self._plain(art["body_html"].split("</h2>", 1)[1] if "</h2>" in art["body_html"] else art["body_html"])
            excerpt = plain[:280].rsplit(" ", 1)[0] + "…"
            a = Article(title=art["title"], excerpt=excerpt, content=html, category=cats["مقالات"],
                        author_name=art["author"].replace(" / ", " — "), published=True, published_at=timezone.now())
            self._attach(a.cover_image, self._img(cover)); a.save()
            self.stdout.write(self.style.SUCCESS(f"Seeded article «{a.title}»."))
        self._article_seo()

    # Tags are taken from phrases that actually appear in each article's text; descriptions only restate the
    # article's own abstract. Filled only where empty so the client's later edits are never overwritten.
    ARTICLE_SEO = {
        "نور و مسئولیت شهری در دوران بحران انرژی": {
            "seo_title": "نور و مسئولیت شهری در دوران بحران انرژی",
            "seo_description": "بررسی نور شهری از دیدگاه مسئولیت: مصرف انرژی، آلودگی نوری و کیفیت زیست انسان و محیط در دوران بحران انرژی.",
            "tags": ["نورپردازی شهری", "مسئولیت شهری", "بحران انرژی", "بهره‌وری انرژی", "آلودگی نوری", "کنترل هوشمند نور"],
        },
        "نورپردازی شهری؛ پیوند علم، هنر و فناوری در خلق هویت شبانه شهر": {
            "seo_title": "نورپردازی شهری: علم، هنر و فناوری در هویت شبانه شهر",
            "seo_description": "نور شهری از دیدگاه فنی، هنری و اجتماعی؛ نقش آن در هویت‌سازی، پایداری زیست‌محیطی و توسعه‌ی شهری.",
            "tags": ["نورپردازی شهری", "طراحی نور", "هویت شهری", "پایداری زیست‌محیطی", "فناوری‌های نوین نورپردازی", "آلودگی نوری"],
        },
    }

    FIG_ALTS = {
        "article1_fig1": "تصویر مفهومی خیابان شهری در شب با تیر روشنایی خورشیدی و ساختمان‌های بلند",
        "article2_fig1": "نمای شبانه‌ی تهران با برج میلاد و روشنایی شهر",
    }

    def _article_seo(self):
        from apps.articles.models import Tag
        for title, d in self.ARTICLE_SEO.items():
            a = Article.objects.filter(title=title).first()
            if not a:
                continue
            changed = False
            for f in ("seo_title", "seo_description"):
                if not getattr(a, f):
                    setattr(a, f, d[f]); changed = True
            for fig, alt in self.FIG_ALTS.items():
                import re as _re
                new = _re.sub(r'(<img src="[^"]*%s[^"]*") alt=""' % fig, r'\1 alt="%s"' % alt, a.content)
                if new != a.content:
                    a.content = new; changed = True
            if a.excerpt.startswith("چکیده"):
                a.excerpt = a.excerpt[len("چکیده"):].strip(); changed = True
            if changed:
                a.save()
            if not a.tags.exists():
                a.tags.set([Tag.objects.get_or_create(title=t)[0] for t in d["tags"]])

    @staticmethod
    def _plain(html):
        import re
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()

    @staticmethod
    def _wrap_abstract(html):
        """Wrap the «چکیده» heading + its content in a highlighted box."""
        import re
        m = re.search(r"<h2>چکیده</h2>(.*?)(?=<h2>)", html, flags=re.S)
        if not m:
            return html
        return html[:m.start()] + '<div class="abstract-box"><h2>چکیده</h2>' + m.group(1) + "</div>" + html[m.end():]


    # ------------------------------------------------------------ SEO polish
    # Alt texts below were written from the actual photos (each unique, no keyword stuffing). They replace only the
    # generic seed values (alt == title / empty), so anything the client edited is never overwritten.
    HK_ALTS = ['المان نوری هفت\u200cخان رستم با قاب مشبک و نقش رستم، آویخته بر عرض خیابان در غروب', 'نمای دور المان نوری هفت\u200cخان رستم بالای خیابان، با ساختمان\u200cها و خودروها در غروب', 'المان نوری رنگی هفت\u200cخان رستم آویخته بر عرض خیابان در غروب', 'المان نوری هفت\u200cخان رستم در شب، بالای بلوار و چراغ\u200cهای خیابان', 'المان نوری رستم سوار بر رخش بالای خیابانی شبانه', 'المان نوری هفت\u200cخان رستم با کتیبه\u200cهای خوشنویسی بالای خیابان در شب', 'المان نوری هفت\u200cخان رستم در گرگ\u200cومیش، با جرثقیل نصب در پایین تصویر', 'المان نوری هفت\u200cخان رستم با نقش قرمز و آبی در شب', 'المان نوری افقی هفت\u200cخان رستم با نقش سوارکار در شب', 'المان نوری رنگارنگ هفت\u200cخان رستم با کتیبه\u200cهای خوشنویسی در شب', 'المان نوری هفت\u200cخان رستم بالای خیابانی تاریک در شب', 'دو عضو تیم پرتو نور در حال بررسی نقشه\u200cی طرح، مقابل المان نئونی', 'ترسیم و بازبینی طرح روی میز کار در کارگاه', 'بازبینی طرح خطی رستم روی المان نئونی در کارگاه', 'جزئیات خطوط نئون رنگی و خوشنویسی روی المان در کارگاه', 'کنترل المان نئونی توسط یکی از اعضای تیم در کارگاه', 'اتصال و سیم\u200cکشی قاب المان با دریل', 'دو نفر از تیم در حال اتصال و سیم\u200cکشی قاب المان کنار خیابان', 'نصب بخشی از قاب نورانی المان روی کامیون', 'یکی از اعضای تیم مقابل المان نئونی بارگیری\u200cشده در شب', 'بارگیری قاب المان روی کامیون با جرثقیل', 'نصب شبانه\u200cی المان با جرثقیل در خیابان', 'نصب المان با جرثقیل بر عرض خیابان در غروب', 'المان آویخته بر عرض خیابان هنگام نصب با جرثقیل', 'عضوی از تیم کنار خیابان هنگام نصب المان با جرثقیل', 'نصب شبانه\u200cی المان با جرثقیل در خیابانی با نخل', 'نمای نزدیک نصب المان روی سبد بالابر', 'نصب نقش نورانی المان با سبد بالابر در غروب', 'نصب المان با سبد بالابر کامیون در انتهای خیابان', 'عضوی از تیم پرتو نور در خیابان محل اجرا در نور غروب', 'دو نفر در خیابان شبانه پس از روشن\u200cشدن المان\u200cها']
    PRODUCT_ALTS = ['ریسه\u200cی نوری گل\u200cدار و دانه\u200cبرفی در نمای بالا از خیابان شبانه', 'ریسه\u200cی نوری با نقش ماهی عرض خیابان در شب', 'ریسه\u200cی نوری سبز با نقش خورشید و ماه در مرکز، در شب']
    STAGE_TEXT = {
        "design": "طراحی نقش‌ها و بازبینی طرح خطی روی نقشه و میز کار، پیش از ساخت.",
        "build": "ساخت المان با خطوط نئون و خوشنویسی، اتصال و سیم‌کشی و کنترل نهایی پیش از نصب.",
        "install": "بارگیری با جرثقیل و نصب شبانه‌ی المان‌ها روی عرض خیابان.",
    }

    def _seo_polish(self):
        p = Project.objects.filter(slug="haft-khan-rostam").first()
        if p:
            if not p.seo_title:
                p.seo_title = "هفت‌خان رستم: المان‌های نوری داستانی شاهنامه‌ای"
            if not p.seo_description:
                p.seo_description = "مطالعه‌ی موردی پروژه‌ی هفت‌خان رستم: طراحی، ساخت و نصب شبانه‌ی المان‌های نوری داستانی شاهنامه‌ای روی خیابان، همه‌ی مراحل توسط تیم پرتو نور."
            if not p.design_concept:
                p.design_concept = self.STAGE_TEXT["design"]
            if not p.manufacturing_notes:
                p.manufacturing_notes = self.STAGE_TEXT["build"]
            if not p.execution_notes:
                p.execution_notes = self.STAGE_TEXT["install"]
            p.save()
            for i, img in enumerate(p.images.order_by("display_order", "id")):
                if i < len(self.HK_ALTS) and (not img.alt_text or img.alt_text == img.title or img.alt_text == p.title):
                    img.alt_text = self.HK_ALTS[i]; img.save(update_fields=["alt_text"])
            story = GalleryItem.objects.filter(category__title="المان‌های نوری داستانی").order_by("display_order", "id")
            for i, it in enumerate(story):
                if i < len(self.HK_ALTS) and (not it.alt_text or it.alt_text == it.title):
                    it.alt_text = self.HK_ALTS[i]; it.save(update_fields=["alt_text"])
                if it.project_id is None:
                    it.project = p; it.save(update_fields=["project"])
        prod = Product.objects.filter(slug="risheh").first()
        if prod:
            if not prod.seo_title:
                prod.seo_title = "ریسه نوری عرض خیابانی؛ ثبت سفارش از پرتو نور"
            if not prod.seo_description:
                prod.seo_description = "ریسه نوری اختصاصی پرتو نور با کیفیت هم‌سطح نمونه‌های خارجی، قیمت مناسب‌تر و مقاومت بالا در برابر شرایط آب‌وهوایی؛ فرم ثبت سفارش آنلاین."
            prod.save()
            for i, img in enumerate(prod.images.order_by("display_order", "id")):
                if i < len(self.PRODUCT_ALTS) and (not img.alt_text or img.alt_text == prod.title):
                    img.alt_text = self.PRODUCT_ALTS[i]; img.save(update_fields=["alt_text"])

    def _process_steps(self):
        if ProcessStep.objects.exists():
            return
        for i, (t, d) in enumerate(PROCESS):
            ProcessStep.objects.create(title=t, description=d, display_order=i, published=True)

    # ------------------------------------------------------------- navigation
    def _navigation(self, reset):
        main, _ = Navigation.objects.get_or_create(slot="main")
        foot, _ = Navigation.objects.get_or_create(slot="footer")
        if reset:
            main.items.all().delete(); foot.items.all().delete()
        if not main.items.exists():
            for i, (t, u) in enumerate([("خانه", "/"), ("فلسفه پرتو نور", "/about/"), ("آثار", "/gallery/"), ("ریسه", "/products/"),
                                        ("خدمات و راهکارها", "/services/"), ("مجله نورپردازی شهری", "/articles/"), ("تماس با ما", "/contact/")]):
                NavigationItem.objects.create(navigation=main, title=t, url=u, display_order=i)
        if not foot.items.exists():
            for i, (t, u) in enumerate([("درباره ما", "/about/"), ("آثار", "/gallery/"), ("پروژه‌ها", "/projects/"), ("مقالات", "/articles/"), ("تماس", "/contact/")]):
                NavigationItem.objects.create(navigation=foot, title=t, url=u, display_order=i)

    # --------------------------------------------------------------- homepage
    def _homepage(self, reset):
        video = ASSETS / ("company_video_web.mp4" if (ASSETS / "company_video_web.mp4").exists() else "company_video.mp4")
        plan = [  # (type, order, fields, image key)
            ("hero", 0, dict(title="طراحی، ساخت و اجرای المان‌های نوری شهری",
                             subtitle="نورپردازی اختصاصی برای هر شهر؛ از نیازسنجی تا نصب و پشتیبانی.",
                             cta_label="مشاهده آثار", cta_url="/gallery/"), "luster-01"),
            ("brand_intro", 1, dict(title="نور مسئول",
                                    subtitle="نور مسئول، نوری است که از انرژی آگاه است؛ از تاریکی نمی‌ترسد؛ و از انسان فراتر می‌اندیشد."), "luster-02"),
            ("differentiator", 2, {}, None),
            ("featured_projects", 3, {}, None),
            ("gallery", 4, dict(title="آثار ما در شهرها", subtitle="از المان‌های داستانی تا لوسترهای نوری شهری و ریسه‌های عرض خیابانی."), None),
            ("services", 5, dict(title="از نخستین بازدید تا پشتیبانی"), None),
            ("product_highlight", 6, dict(cta_label="ثبت سفارش ریسه"), None),
            ("workshop", 7, {}, None),
            ("company_video", 8, dict(title="پرتو نور را از نزدیک ببینید", subtitle="ویدیوی معرفی شرکت"), None),
            ("cta", 9, dict(cta_label="درخواست مشاوره", cta_url="/contact/#consultation"), None),
        ]
        visible = {p[0] for p in plan}
        for sec in HomepageSection.objects.all():
            if sec.section_type not in visible and reset:
                sec.is_visible = False; sec.save()
        for stype, order, fields, key in plan:
            sec, created = HomepageSection.objects.get_or_create(section_type=stype, defaults={"display_order": order, "published": True})
            if not (created or reset or not sec.is_visible):
                continue
            for k, v in fields.items():
                if reset or not getattr(sec, k):
                    setattr(sec, k, v)
            sec.display_order = order
            if key and (reset or not sec.image):
                self._attach(sec.image, self._img(key))
            if stype == "company_video" and (reset or not sec.video):
                self._attach(sec.video, video)
                poster = ASSETS / "company_video_poster.jpg"
                if poster.exists():
                    self._attach(sec.video_poster, poster)
            sec.is_visible = True
            sec.save()
