"""
Seeds the REAL client-provided material as normal, fully editable database content:
work categories (from the client's handwritten sheet), the curated photos, the
Haft Khan Rostam case study, the Ø±ÛŒØ³Ù‡ product, services, the two real articles
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

# Order and names exactly as written on the client's sheet under Â«Ø¢Ø«Ø§Ø±Â».
CATEGORIES = [
    "Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø²Ù…ÛŒÙ†ÛŒ Ùˆ Ù…Ù†Ø§Ø³Ø¨ØªÛŒ",
    "Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ",
    "Ù„ÙˆØ³ØªØ±Ù‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø´Ù‡Ø±ÛŒ",
    "Ø±ÛŒØ³Ù‡â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù†ÛŒ",
    "Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø¯ÛŒÙ†Ø§Ù…ÛŒÚ©",
    "Ù…Ø­ØµÙˆÙ„ Ø§Ø®ØªØµØ§ØµÛŒ Ø±ÛŒØ³Ù‡ Ù†ÙˆØ±ÛŒ",
    "Ú©Ø§ØªØ§Ù„ÙˆÚ¯",
]

SERVICES = [  # titles from the client's sheet Â«Ø®Ø¯Ù…Ø§Øª Ùˆ Ø±Ø§Ù‡Ú©Ø§Ø±Ù‡Ø§Â»
    ("Ø¨Ø§Ø²Ø¯ÛŒØ¯", "Ø¢ØºØ§Ø² Ù‡Ø± Ù¾Ø±ÙˆÚ˜Ù‡ Ø¨Ø§ Ø¨Ø§Ø²Ø¯ÛŒØ¯ Ù…ÛŒØ¯Ø§Ù†ÛŒ Ø§Ø² Ù…Ø­Ù„ Ùˆ Ø´Ù†Ø§Ø®Øª Ø´Ø±Ø§ÛŒØ· ÙˆØ§Ù‚Ø¹ÛŒ ÙØ¶Ø§.", "proc-team-02"),
    ("Ø´Ù†Ø§Ø®Øª ÙØ±Ù‡Ù†Ú¯ Ùˆ Ø¯Ø§Ø³ØªØ§Ù†â€ŒÙ‡Ø§ Ø¬Ù‡Øª Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ", "Ù†ÙˆØ± Ø®ÙˆØ¨ Ø§Ø² Ø¯Ø§Ø³ØªØ§Ù† Ø´Ù‡Ø± Ù…ÛŒâ€ŒØ¢ÛŒØ¯Ø› ÙØ±Ù‡Ù†Ú¯ØŒ ØªØ§Ø±ÛŒØ® Ùˆ Ø±ÙˆØ§ÛŒØªâ€ŒÙ‡Ø§ÛŒ Ù…Ø­Ù„ÛŒ Ù¾Ø§ÛŒÙ‡â€ŒÛŒ Ø·Ø±Ø§Ø­ÛŒ Ù…Ø§ Ù‡Ø³ØªÙ†Ø¯.", "story-06"),
    ("Ù…Ø·Ø§Ù„Ø¹Ù‡ Ù…Ø¹Ù…Ø§Ø±ÛŒ ÙØ¶Ø§ Ùˆ Ù…Ú©Ø§Ù†", "Ø¨Ø±Ø±Ø³ÛŒ Ù…Ø¹Ù…Ø§Ø±ÛŒØŒ Ù…Ù‚ÛŒØ§Ø³ Ùˆ Ù…Ø³ÛŒØ±Ù‡Ø§ÛŒ Ø¯ÛŒØ¯ ØªØ§ Ù†ÙˆØ± Ø¨Ø§ ÙØ¶Ø§ Ù‡Ù…â€ŒØ³Ø®Ù† Ø¨Ø§Ø´Ø¯.", "luster-03"),
    ("Ø·Ø±Ø§Ø­ÛŒ Ø§Ø®ØªØµØ§ØµÛŒ", "Ø·Ø±Ø§Ø­ÛŒ Ø§Ù„Ù…Ø§Ù† Ùˆ Ø±Ø§Ù‡Ú©Ø§Ø± Ù†ÙˆØ±ÛŒ Ù…ØªÙ†Ø§Ø³Ø¨ Ø¨Ø§ Ø´Ù‡Ø±ØŒ Ù…Ø­ÛŒØ· Ùˆ Ù…ÙÙ‡ÙˆÙ… Ù¾Ø±ÙˆÚ˜Ù‡.", "proc-design-02"),
    ("Ø³Ø§Ø®Øª", "Ø³Ø§Ø®Øª Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø·Ø±Ø§Ø­ÛŒâ€ŒØ´Ø¯Ù‡.", "proc-build-04"),
    ("Ù†ØµØ¨", "Ù†ØµØ¨ Ùˆ Ø§Ø¬Ø±Ø§ÛŒ Ù¾Ø±ÙˆÚ˜Ù‡ Ø¯Ø± Ù…Ø­Ù„.", "proc-install-03"),
    ("Ù¾Ø´ØªÛŒØ¨Ø§Ù†ÛŒ", "Ù‡Ù…Ø±Ø§Ù‡ÛŒ Ù¾Ø³ Ø§Ø² Ø§Ø¬Ø±Ø§ Ø¨Ø±Ø§ÛŒ Ù†Ú¯Ù‡Ø¯Ø§Ø±ÛŒ Ùˆ Ø±ÙØ¹ Ø§Ø´Ú©Ø§Ù„.", "proc-team-01"),
]

RISHEH_FEATURES = [  # advantages exactly as stated by the client
    ("Ú©ÛŒÙÛŒØª Ù‡Ù…â€ŒØ³Ø·Ø­ Ù…Ø­ØµÙˆÙ„Ø§Øª Ø®Ø§Ø±Ø¬ÛŒ", "Ø³Ø§Ø®Øª Ø¨Ø§ Ù…Ø¹ÛŒØ§Ø±Ù‡Ø§ÛŒ Ú©ÛŒÙÛŒ Ù‡Ù…ØªØ±Ø§Ø² Ù†Ù…ÙˆÙ†Ù‡â€ŒÙ‡Ø§ÛŒ ÙˆØ§Ø±Ø¯Ø§ØªÛŒ."),
    ("Ù‚ÛŒÙ…Øª Ù…Ù†Ø§Ø³Ø¨â€ŒØªØ±", "ØªÙˆÙ„ÛŒØ¯ Ø¯Ø§Ø®Ù„ Ùˆ Ù‚ÛŒÙ…Øª Ø±Ù‚Ø§Ø¨ØªÛŒâ€ŒØªØ± Ù†Ø³Ø¨Øª Ø¨Ù‡ Ù†Ù…ÙˆÙ†Ù‡â€ŒÙ‡Ø§ÛŒ Ø®Ø§Ø±Ø¬ÛŒ."),
    ("Ù…Ù‚Ø§ÙˆÙ…Øª Ø¨Ø§Ù„Ø§ Ø¯Ø± Ø¨Ø±Ø§Ø¨Ø± Ø´Ø±Ø§ÛŒØ· Ø¢Ø¨â€ŒÙˆÙ‡ÙˆØ§ÛŒÛŒ", "Ø·Ø±Ø§Ø­ÛŒâ€ŒØ´Ø¯Ù‡ Ø¨Ø±Ø§ÛŒ ÙØ¶Ø§ÛŒ Ø¨Ø§Ø² Ùˆ Ø´Ø±Ø§ÛŒØ· Ø¬ÙˆÛŒ Ø³Ø®Øª."),
    ("Ú©ÛŒÙÛŒØª Ù†ÙˆØ± Ø¨Ø§Ù„Ø§", "Ù†ÙˆØ± Ø±ÙˆØ´Ù†ØŒ ÛŒÚ©Ù†ÙˆØ§Ø®Øª Ùˆ Ø´ÙØ§Ù."),
    ("Ù‚Ø§Ø¨Ù„ÛŒØª Ø§Ø³ØªÙØ§Ø¯Ù‡ Ø¯Ø± Ù¾Ø±ÙˆÚ˜Ù‡â€ŒÙ‡Ø§ÛŒ Ù…Ø®ØªÙ„Ù", "Ù…Ù†Ø§Ø³Ø¨ Ø®ÛŒØ§Ø¨Ø§Ù† Ùˆ Ù…ÛŒØ¯Ø§Ù†ØŒ Ù…Ù†Ø§Ø³Ø¨Øªâ€ŒÙ‡Ø§ØŒ ÙØ¶Ø§Ù‡Ø§ÛŒ ØªØ¬Ø§Ø±ÛŒ Ùˆ Ù…Ø¬Ù…ÙˆØ¹Ù‡â€ŒÙ‡Ø§."),
    ("Ø§Ø±Ø§Ø¦Ù‡ Ù…ØªÙ†Ø§Ø³Ø¨ Ø¨Ø§ Ù†ÛŒØ§Ø² Ù¾Ø±ÙˆÚ˜Ù‡", "Ù…Ù‚Ø¯Ø§Ø±ØŒ Ø±Ù†Ú¯ Ùˆ Ù†ÙˆØ¹ Ø§Ø¬Ø±Ø§ Ø¨Ø± Ø§Ø³Ø§Ø³ Ù†ÛŒØ§Ø² Ù‡Ø± Ù¾Ø±ÙˆÚ˜Ù‡."),
]


PROCESS = [  # the company's real workflow, as defined by the client
    ("Ù†ÛŒØ§Ø²Ø³Ù†Ø¬ÛŒ", "Ø´Ù†ÛŒØ¯Ù† Ù†ÛŒØ§Ø² Ùˆ Ù‡Ø¯Ù Ø´Ù‡Ø± ÛŒØ§ Ù…Ø¬Ù…ÙˆØ¹Ù‡."),
    ("Ø¨Ø§Ø²Ø¯ÛŒØ¯ Ùˆ Ø´Ù†Ø§Ø®Øª ÙØ¶Ø§", "Ø¨Ø§Ø²Ø¯ÛŒØ¯ Ù…ÛŒØ¯Ø§Ù†ÛŒ Ùˆ Ø´Ù†Ø§Ø®Øª Ù…Ø¹Ù…Ø§Ø±ÛŒØŒ Ù…Ú©Ø§Ù†ØŒ ÙØ±Ù‡Ù†Ú¯ Ùˆ Ø¯Ø§Ø³ØªØ§Ù† Ù…Ø­Ù„."),
    ("Ø·Ø±Ø§Ø­ÛŒ Ø§Ø®ØªØµØ§ØµÛŒ", "Ø·Ø±Ø§Ø­ÛŒ Ø§Ù„Ù…Ø§Ù† ÛŒØ§ Ø±Ø§Ù‡Ú©Ø§Ø± Ù†ÙˆØ±ÛŒ Ù…ØªÙ†Ø§Ø³Ø¨ Ø¨Ø§ Ù‡Ù…Ø§Ù† Ù¾Ø±ÙˆÚ˜Ù‡."),
    ("Ø¨Ø±Ø±Ø³ÛŒ Ùˆ Ù…Ù‡Ù†Ø¯Ø³ÛŒ", "Ø¨Ø±Ø±Ø³ÛŒ ÙÙ†ÛŒ Ùˆ Ù…Ù‡Ù†Ø¯Ø³ÛŒ Ø·Ø±Ø­ Ù¾ÛŒØ´ Ø§Ø² Ø³Ø§Ø®Øª."),
    ("Ø³Ø§Ø®Øª", "Ø³Ø§Ø®Øª Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§."),
    ("Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ", "Ø§Ø¬Ø±Ø§ÛŒ Ù†ÙˆØ± Ùˆ ØªÙ†Ø¸ÛŒÙ… Ø¢Ù† Ø±ÙˆÛŒ Ø§Ù„Ù…Ø§Ù†."),
    ("Ù†ØµØ¨ Ùˆ Ø§Ø¬Ø±Ø§", "Ù†ØµØ¨ Ùˆ Ø±Ø§Ù‡â€ŒØ§Ù†Ø¯Ø§Ø²ÛŒ Ø¯Ø± Ù…Ø­Ù„ Ù¾Ø±ÙˆÚ˜Ù‡."),
    ("Ù¾Ø´ØªÛŒØ¨Ø§Ù†ÛŒ", "Ù‡Ù…Ø±Ø§Ù‡ÛŒ Ù¾Ø³ Ø§Ø² Ø§Ø¬Ø±Ø§."),
]


class Command(BaseCommand):
    help = "Seed real client content (categories, works, project, product, services, articles, menus, homepage)."

    def add_arguments(self, parser):
        for f in ("works", "project", "nav", "home", "product"):
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
        product = self._product(o["reset_product"])
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
        # logos smaller than 160px/96px and show a vector mark instead â€” replace with the real logo.
        for name in ("logo_symbol", "logo_full"):
            if not getattr(s, name) and (ASSETS / "logo_symbol.png").exists():
                self._attach(getattr(s, name), ASSETS / "logo_symbol.png"); changed = True
        # Contact details supplied by the client (the only ones they have; no address/e-mail exist).
        if not s.phone:
            s.phone = "09156249754"; changed = True
        if not s.instagram_url:
            s.instagram_url = "https://www.instagram.com/partonoor.co/"; changed = True
        if not s.slogan:
            s.slogan = "Ø·Ø±Ø§Ø­ÛŒØŒ Ø³Ø§Ø®Øª Ùˆ Ø§Ø¬Ø±Ø§ÛŒ Ø±Ø§Ù‡Ú©Ø§Ø±Ù‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø§Ø®ØªØµØ§ØµÛŒ Ø´Ù‡Ø±ÛŒ"; changed = True
        if not s.default_seo_title:
            s.default_seo_title = "Ù¾Ø±ØªÙˆ Ù†ÙˆØ± | Ø·Ø±Ø§Ø­ÛŒØŒ Ø³Ø§Ø®Øª Ùˆ Ø§Ø¬Ø±Ø§ÛŒ Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ùˆ Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø´Ù‡Ø±ÛŒ"; changed = True
        if not s.default_seo_description:
            s.default_seo_description = "Ù¾Ø±ØªÙˆ Ù†ÙˆØ±: Ø·Ø±Ø§Ø­ÛŒ Ùˆ Ø³Ø§Ø®Øª Ø§Ø®ØªØµØ§ØµÛŒ Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒØŒ Ù„ÙˆØ³ØªØ± Ù†ÙˆØ±ÛŒ Ø´Ù‡Ø±ÛŒØŒ Ø±ÛŒØ³Ù‡ Ù†ÙˆØ±ÛŒ Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù†ÛŒ Ùˆ Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø¯ÛŒÙ†Ø§Ù…ÛŒÚ©Ø› Ø§Ø² Ù†ÛŒØ§Ø²Ø³Ù†Ø¬ÛŒ ØªØ§ Ù†ØµØ¨ Ùˆ Ù¾Ø´ØªÛŒØ¨Ø§Ù†ÛŒ."; changed = True
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
            self.stdout.write("Works already exist â€” skipping (use --reset-works to re-seed).")
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
        self.stdout.write(self.style.SUCCESS(f"Seeded {n} works ({GalleryItem.objects.filter(needs_review=True).count()} flagged Â«Ø¯Ø± Ø§Ù†ØªØ¸Ø§Ø± ØªØ£ÛŒÛŒØ¯Â»)."))

    # ---------------------------------------------------------------- project
    def _project(self, reset):
        slug = "haft-khan-rostam"
        if reset:
            Project.objects.filter(slug=slug).delete()
        p = Project.objects.filter(slug=slug).first()
        if p:
            return p
        cat, _ = ProjectCategory.objects.get_or_create(title="Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ")
        p = Project(
            title="Ù‡ÙØªâ€ŒØ®Ø§Ù† Ø±Ø³ØªÙ…", slug=slug, category=cat, featured=True, published=True, display_order=0,
            short_description="Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ Ú©Ù‡ Ø±ÙˆØ§ÛŒØª Ø´Ø§Ù‡Ù†Ø§Ù…Ù‡â€ŒØ§ÛŒ Ù‡ÙØªâ€ŒØ®Ø§Ù† Ø±Ø³ØªÙ… Ø±Ø§ Ø¨Ù‡ Ø®ÛŒØ§Ø¨Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ø´Ù‡Ø± Ù…ÛŒâ€ŒØ¢ÙˆØ±Ù†Ø¯.",
            full_description=(
                "Â«Ù‡ÙØªâ€ŒØ®Ø§Ù† Ø±Ø³ØªÙ…Â» Ù…Ø¬Ù…ÙˆØ¹Ù‡â€ŒØ§ÛŒ Ø§Ø² Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ Ø§Ø³Øª Ú©Ù‡ ØµØ­Ù†Ù‡â€ŒÙ‡Ø§ÛŒ Ø´Ø§Ù‡Ù†Ø§Ù…Ù‡ Ø±Ø§ Ø¨Ø§ Ø®Ø·ÙˆØ· Ù†ÙˆØ± Ùˆ Ø®ÙˆØ´Ù†ÙˆÛŒØ³ÛŒ Ø±ÙˆÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ø´Ù‡Ø± Ø±ÙˆØ§ÛŒØª Ù…ÛŒâ€ŒÚ©Ù†Ø¯.\n\n"
                "Ø§ÛŒÙ† Ù¾Ø±ÙˆÚ˜Ù‡ Ø¯Ø± ØªÙ…Ø§Ù… Ù…Ø±Ø§Ø­Ù„ØŒ Ø§Ø² Ø·Ø±Ø§Ø­ÛŒ Ù†Ù‚Ø´ Ùˆ Ø³Ø§Ø®Øª Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ ØªØ§ Ù†ØµØ¨ Ø´Ø¨Ø§Ù†Ù‡ Ø±ÙˆÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†ØŒ ØªÙˆØ³Ø· ØªÛŒÙ… Ù¾Ø±ØªÙˆ Ù†ÙˆØ± Ø§Ù†Ø¬Ø§Ù… Ø´Ø¯Ù‡ Ø§Ø³Øª."
            ),
        )
        self._attach(p.cover_image, self._img("story-01"))
        p.save()
        stage_of = {"design": "design", "build": "build", "install": "install", "team": "install", "": "result", "hero": "result"}
        order = 0
        for m in self.manifest:
            in_story = m["category"] == "Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ"
            is_proc = m["id"].startswith("proc-")
            if not (in_story or is_proc) or not m["visible"]:
                continue
            img = ProjectImage(project=p, title=m["title"], alt_text=m["title"] or p.title, stage=stage_of[m["role"]], display_order=order, active=True)
            self._attach(img.image, self._img(m["id"])); img.save(); order += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded project Â«Ù‡ÙØªâ€ŒØ®Ø§Ù† Ø±Ø³ØªÙ…Â» with {order} staged photos."))
        return p

    # ---------------------------------------------------------------- product
    def _product(self, reset=False):
        prod = Product.objects.filter(slug="risheh").first()`r`n        if prod:`r`n            self._attach(prod.main_image, self._img("garland-01")); prod.save()`r`n            for i, key in enumerate(("garland-02", "garland-03", "garland-04")):`r`n                pi = prod.images.filter(display_order=i).first()`r`n                if pi:`r`n                    self._attach(pi.image, self._img(key)); pi.save()`r`n            return prod
        prod = Product(
            title="Ø±ÛŒØ³Ù‡ Ù†ÙˆØ±ÛŒ Ù¾Ø±ØªÙˆ Ù†ÙˆØ±", slug="risheh", published=True, display_order=0,
            order_cta_label="Ø«Ø¨Øª Ø³ÙØ§Ø±Ø´ Ø±ÛŒØ³Ù‡",
            short_description="Ø±ÛŒØ³Ù‡ Ù†ÙˆØ±ÛŒ Ø§Ø®ØªØµØ§ØµÛŒ Ø¨Ø§ Ú©ÛŒÙÛŒØª Ù‡Ù…â€ŒØ³Ø·Ø­ Ù†Ù…ÙˆÙ†Ù‡â€ŒÙ‡Ø§ÛŒ Ø®Ø§Ø±Ø¬ÛŒØŒ Ù‚ÛŒÙ…Øª Ù…Ù†Ø§Ø³Ø¨â€ŒØªØ± Ùˆ Ù…Ù‚Ø§ÙˆÙ…Øª Ø¨Ø§Ù„Ø§ Ø¯Ø± Ø¨Ø±Ø§Ø¨Ø± Ø´Ø±Ø§ÛŒØ· Ø¢Ø¨â€ŒÙˆÙ‡ÙˆØ§ÛŒÛŒ.",
            full_description=(
                "Ø±ÛŒØ³Ù‡â€ŒÛŒ Ù¾Ø±ØªÙˆ Ù†ÙˆØ± Ù…Ø­ØµÙˆÙ„ÛŒ Ø§Ø³Øª Ú©Ù‡ Ø®ÙˆØ¯Ù…Ø§Ù† ØªÙˆÙ„ÛŒØ¯ Ù…ÛŒâ€ŒÚ©Ù†ÛŒÙ… Ùˆ Ø¨Ø±Ø§ÛŒ Ù¾Ø±ÙˆÚ˜Ù‡â€ŒÙ‡Ø§ÛŒ Ù…Ø®ØªÙ„Ù Ù‚Ø§Ø¨Ù„ Ø³ÙØ§Ø±Ø´ Ø§Ø³Øª.\n\n"
                "Ú©ÛŒÙÛŒØª Ù†ÙˆØ± Ø¨Ø§Ù„Ø§ØŒ Ù…Ù‚Ø§ÙˆÙ…Øª Ø¯Ø± Ø¨Ø±Ø§Ø¨Ø± Ø´Ø±Ø§ÛŒØ· Ø¢Ø¨â€ŒÙˆÙ‡ÙˆØ§ÛŒÛŒ Ùˆ Ø§Ù…Ú©Ø§Ù† Ø§Ø±Ø§Ø¦Ù‡ Ù…ØªÙ†Ø§Ø³Ø¨ Ø¨Ø§ Ù†ÛŒØ§Ø² Ù‡Ø± Ù¾Ø±ÙˆÚ˜Ù‡ØŒ Ø¢Ù† Ø±Ø§ Ø¨Ø±Ø§ÛŒ Ø§Ø¬Ø±Ø§ Ø¯Ø± Ø®ÛŒØ§Ø¨Ø§Ù†ØŒ Ù…ÛŒØ¯Ø§Ù† Ùˆ ÙØ¶Ø§Ù‡Ø§ÛŒ ØªØ¬Ø§Ø±ÛŒ Ù…Ù†Ø§Ø³Ø¨ Ù…ÛŒâ€ŒÚ©Ù†Ø¯."
            ),
        )
        self._attach(prod.main_image, self._img("garland-01"))
        prod.save()
        for i, (t, d) in enumerate(RISHEH_FEATURES):
            ProductFeature.objects.create(product=prod, title=t, description=d, display_order=i)
        for i, key in enumerate(("garland-02", "garland-03", "garland-04")):
            pi = ProductImage(product=prod, alt_text="Ø±ÛŒØ³Ù‡ Ù†ÙˆØ±ÛŒ Ù¾Ø±ØªÙˆ Ù†ÙˆØ±", display_order=i)
            self._attach(pi.image, self._img(key)); pi.save()
        self.stdout.write(self.style.SUCCESS("Seeded product Â«Ø±ÛŒØ³Ù‡Â»."))
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
        for i, t in enumerate(["Ù…Ù‚Ø§Ù„Ø§Øª", "Ø§ÛŒØ¯Ù‡â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ", "Ù…ØªØ±ÛŒØ§Ù„ Ùˆ ØªÚ©Ù†ÙˆÙ„ÙˆÚ˜ÛŒ", "Ø§Ø®Ø¨Ø§Ø± Ùˆ Ø±ÙˆÛŒØ¯Ø§Ø¯Ù‡Ø§"]):
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
            excerpt = plain[:280].rsplit(" ", 1)[0] + "â€¦"
            a = Article(title=art["title"], excerpt=excerpt, content=html, category=cats["Ù…Ù‚Ø§Ù„Ø§Øª"],
                        author_name=art["author"].replace(" / ", " â€” "), published=True, published_at=timezone.now())
            self._attach(a.cover_image, self._img(cover)); a.save()
            self.stdout.write(self.style.SUCCESS(f"Seeded article Â«{a.title}Â»."))
        self._article_seo()

    # Tags are taken from phrases that actually appear in each article's text; descriptions only restate the
    # article's own abstract. Filled only where empty so the client's later edits are never overwritten.
    ARTICLE_SEO = {
        "Ù†ÙˆØ± Ùˆ Ù…Ø³Ø¦ÙˆÙ„ÛŒØª Ø´Ù‡Ø±ÛŒ Ø¯Ø± Ø¯ÙˆØ±Ø§Ù† Ø¨Ø­Ø±Ø§Ù† Ø§Ù†Ø±Ú˜ÛŒ": {
            "seo_title": "Ù†ÙˆØ± Ùˆ Ù…Ø³Ø¦ÙˆÙ„ÛŒØª Ø´Ù‡Ø±ÛŒ Ø¯Ø± Ø¯ÙˆØ±Ø§Ù† Ø¨Ø­Ø±Ø§Ù† Ø§Ù†Ø±Ú˜ÛŒ",
            "seo_description": "Ø¨Ø±Ø±Ø³ÛŒ Ù†ÙˆØ± Ø´Ù‡Ø±ÛŒ Ø§Ø² Ø¯ÛŒØ¯Ú¯Ø§Ù‡ Ù…Ø³Ø¦ÙˆÙ„ÛŒØª: Ù…ØµØ±Ù Ø§Ù†Ø±Ú˜ÛŒØŒ Ø¢Ù„ÙˆØ¯Ú¯ÛŒ Ù†ÙˆØ±ÛŒ Ùˆ Ú©ÛŒÙÛŒØª Ø²ÛŒØ³Øª Ø§Ù†Ø³Ø§Ù† Ùˆ Ù…Ø­ÛŒØ· Ø¯Ø± Ø¯ÙˆØ±Ø§Ù† Ø¨Ø­Ø±Ø§Ù† Ø§Ù†Ø±Ú˜ÛŒ.",
            "tags": ["Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø´Ù‡Ø±ÛŒ", "Ù…Ø³Ø¦ÙˆÙ„ÛŒØª Ø´Ù‡Ø±ÛŒ", "Ø¨Ø­Ø±Ø§Ù† Ø§Ù†Ø±Ú˜ÛŒ", "Ø¨Ù‡Ø±Ù‡â€ŒÙˆØ±ÛŒ Ø§Ù†Ø±Ú˜ÛŒ", "Ø¢Ù„ÙˆØ¯Ú¯ÛŒ Ù†ÙˆØ±ÛŒ", "Ú©Ù†ØªØ±Ù„ Ù‡ÙˆØ´Ù…Ù†Ø¯ Ù†ÙˆØ±"],
        },
        "Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø´Ù‡Ø±ÛŒØ› Ù¾ÛŒÙˆÙ†Ø¯ Ø¹Ù„Ù…ØŒ Ù‡Ù†Ø± Ùˆ ÙÙ†Ø§ÙˆØ±ÛŒ Ø¯Ø± Ø®Ù„Ù‚ Ù‡ÙˆÛŒØª Ø´Ø¨Ø§Ù†Ù‡ Ø´Ù‡Ø±": {
            "seo_title": "Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø´Ù‡Ø±ÛŒ: Ø¹Ù„Ù…ØŒ Ù‡Ù†Ø± Ùˆ ÙÙ†Ø§ÙˆØ±ÛŒ Ø¯Ø± Ù‡ÙˆÛŒØª Ø´Ø¨Ø§Ù†Ù‡ Ø´Ù‡Ø±",
            "seo_description": "Ù†ÙˆØ± Ø´Ù‡Ø±ÛŒ Ø§Ø² Ø¯ÛŒØ¯Ú¯Ø§Ù‡ ÙÙ†ÛŒØŒ Ù‡Ù†Ø±ÛŒ Ùˆ Ø§Ø¬ØªÙ…Ø§Ø¹ÛŒØ› Ù†Ù‚Ø´ Ø¢Ù† Ø¯Ø± Ù‡ÙˆÛŒØªâ€ŒØ³Ø§Ø²ÛŒØŒ Ù¾Ø§ÛŒØ¯Ø§Ø±ÛŒ Ø²ÛŒØ³Øªâ€ŒÙ…Ø­ÛŒØ·ÛŒ Ùˆ ØªÙˆØ³Ø¹Ù‡â€ŒÛŒ Ø´Ù‡Ø±ÛŒ.",
            "tags": ["Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø´Ù‡Ø±ÛŒ", "Ø·Ø±Ø§Ø­ÛŒ Ù†ÙˆØ±", "Ù‡ÙˆÛŒØª Ø´Ù‡Ø±ÛŒ", "Ù¾Ø§ÛŒØ¯Ø§Ø±ÛŒ Ø²ÛŒØ³Øªâ€ŒÙ…Ø­ÛŒØ·ÛŒ", "ÙÙ†Ø§ÙˆØ±ÛŒâ€ŒÙ‡Ø§ÛŒ Ù†ÙˆÛŒÙ† Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ", "Ø¢Ù„ÙˆØ¯Ú¯ÛŒ Ù†ÙˆØ±ÛŒ"],
        },
    }

    FIG_ALTS = {
        "article1_fig1": "ØªØµÙˆÛŒØ± Ù…ÙÙ‡ÙˆÙ…ÛŒ Ø®ÛŒØ§Ø¨Ø§Ù† Ø´Ù‡Ø±ÛŒ Ø¯Ø± Ø´Ø¨ Ø¨Ø§ ØªÛŒØ± Ø±ÙˆØ´Ù†Ø§ÛŒÛŒ Ø®ÙˆØ±Ø´ÛŒØ¯ÛŒ Ùˆ Ø³Ø§Ø®ØªÙ…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ø¨Ù„Ù†Ø¯",
        "article2_fig1": "Ù†Ù…Ø§ÛŒ Ø´Ø¨Ø§Ù†Ù‡â€ŒÛŒ ØªÙ‡Ø±Ø§Ù† Ø¨Ø§ Ø¨Ø±Ø¬ Ù…ÛŒÙ„Ø§Ø¯ Ùˆ Ø±ÙˆØ´Ù†Ø§ÛŒÛŒ Ø´Ù‡Ø±",
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
            if a.excerpt.startswith("Ú†Ú©ÛŒØ¯Ù‡"):
                a.excerpt = a.excerpt[len("Ú†Ú©ÛŒØ¯Ù‡"):].strip(); changed = True
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
        """Wrap the Â«Ú†Ú©ÛŒØ¯Ù‡Â» heading + its content in a highlighted box."""
        import re
        m = re.search(r"<h2>Ú†Ú©ÛŒØ¯Ù‡</h2>(.*?)(?=<h2>)", html, flags=re.S)
        if not m:
            return html
        return html[:m.start()] + '<div class="abstract-box"><h2>Ú†Ú©ÛŒØ¯Ù‡</h2>' + m.group(1) + "</div>" + html[m.end():]


    # ------------------------------------------------------------ SEO polish
    # Alt texts below were written from the actual photos (each unique, no keyword stuffing). They replace only the
    # generic seed values (alt == title / empty), so anything the client edited is never overwritten.
    HK_ALTS = ['Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¨Ø§ Ù‚Ø§Ø¨ Ù…Ø´Ø¨Ú© Ùˆ Ù†Ù‚Ø´ Ø±Ø³ØªÙ…ØŒ Ø¢ÙˆÛŒØ®ØªÙ‡ Ø¨Ø± Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù† Ø¯Ø± ØºØ±ÙˆØ¨', 'Ù†Ù…Ø§ÛŒ Ø¯ÙˆØ± Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¨Ø§Ù„Ø§ÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†ØŒ Ø¨Ø§ Ø³Ø§Ø®ØªÙ…Ø§Ù†\u200cÙ‡Ø§ Ùˆ Ø®ÙˆØ¯Ø±ÙˆÙ‡Ø§ Ø¯Ø± ØºØ±ÙˆØ¨', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ø±Ù†Ú¯ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¢ÙˆÛŒØ®ØªÙ‡ Ø¨Ø± Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù† Ø¯Ø± ØºØ±ÙˆØ¨', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¯Ø± Ø´Ø¨ØŒ Ø¨Ø§Ù„Ø§ÛŒ Ø¨Ù„ÙˆØ§Ø± Ùˆ Ú†Ø±Ø§Øº\u200cÙ‡Ø§ÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ø±Ø³ØªÙ… Ø³ÙˆØ§Ø± Ø¨Ø± Ø±Ø®Ø´ Ø¨Ø§Ù„Ø§ÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†ÛŒ Ø´Ø¨Ø§Ù†Ù‡', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¨Ø§ Ú©ØªÛŒØ¨Ù‡\u200cÙ‡Ø§ÛŒ Ø®ÙˆØ´Ù†ÙˆÛŒØ³ÛŒ Ø¨Ø§Ù„Ø§ÛŒ Ø®ÛŒØ§Ø¨Ø§Ù† Ø¯Ø± Ø´Ø¨', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¯Ø± Ú¯Ø±Ú¯\u200cÙˆÙ…ÛŒØ´ØŒ Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„ Ù†ØµØ¨ Ø¯Ø± Ù¾Ø§ÛŒÛŒÙ† ØªØµÙˆÛŒØ±', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¨Ø§ Ù†Ù‚Ø´ Ù‚Ø±Ù…Ø² Ùˆ Ø¢Ø¨ÛŒ Ø¯Ø± Ø´Ø¨', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ø§ÙÙ‚ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¨Ø§ Ù†Ù‚Ø´ Ø³ÙˆØ§Ø±Ú©Ø§Ø± Ø¯Ø± Ø´Ø¨', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ø±Ù†Ú¯Ø§Ø±Ù†Ú¯ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¨Ø§ Ú©ØªÛŒØ¨Ù‡\u200cÙ‡Ø§ÛŒ Ø®ÙˆØ´Ù†ÙˆÛŒØ³ÛŒ Ø¯Ø± Ø´Ø¨', 'Ø§Ù„Ù…Ø§Ù† Ù†ÙˆØ±ÛŒ Ù‡ÙØª\u200cØ®Ø§Ù† Ø±Ø³ØªÙ… Ø¨Ø§Ù„Ø§ÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†ÛŒ ØªØ§Ø±ÛŒÚ© Ø¯Ø± Ø´Ø¨', 'Ø¯Ùˆ Ø¹Ø¶Ùˆ ØªÛŒÙ… Ù¾Ø±ØªÙˆ Ù†ÙˆØ± Ø¯Ø± Ø­Ø§Ù„ Ø¨Ø±Ø±Ø³ÛŒ Ù†Ù‚Ø´Ù‡\u200cÛŒ Ø·Ø±Ø­ØŒ Ù…Ù‚Ø§Ø¨Ù„ Ø§Ù„Ù…Ø§Ù† Ù†Ø¦ÙˆÙ†ÛŒ', 'ØªØ±Ø³ÛŒÙ… Ùˆ Ø¨Ø§Ø²Ø¨ÛŒÙ†ÛŒ Ø·Ø±Ø­ Ø±ÙˆÛŒ Ù…ÛŒØ² Ú©Ø§Ø± Ø¯Ø± Ú©Ø§Ø±Ú¯Ø§Ù‡', 'Ø¨Ø§Ø²Ø¨ÛŒÙ†ÛŒ Ø·Ø±Ø­ Ø®Ø·ÛŒ Ø±Ø³ØªÙ… Ø±ÙˆÛŒ Ø§Ù„Ù…Ø§Ù† Ù†Ø¦ÙˆÙ†ÛŒ Ø¯Ø± Ú©Ø§Ø±Ú¯Ø§Ù‡', 'Ø¬Ø²Ø¦ÛŒØ§Øª Ø®Ø·ÙˆØ· Ù†Ø¦ÙˆÙ† Ø±Ù†Ú¯ÛŒ Ùˆ Ø®ÙˆØ´Ù†ÙˆÛŒØ³ÛŒ Ø±ÙˆÛŒ Ø§Ù„Ù…Ø§Ù† Ø¯Ø± Ú©Ø§Ø±Ú¯Ø§Ù‡', 'Ú©Ù†ØªØ±Ù„ Ø§Ù„Ù…Ø§Ù† Ù†Ø¦ÙˆÙ†ÛŒ ØªÙˆØ³Ø· ÛŒÚ©ÛŒ Ø§Ø² Ø§Ø¹Ø¶Ø§ÛŒ ØªÛŒÙ… Ø¯Ø± Ú©Ø§Ø±Ú¯Ø§Ù‡', 'Ø§ØªØµØ§Ù„ Ùˆ Ø³ÛŒÙ…\u200cÚ©Ø´ÛŒ Ù‚Ø§Ø¨ Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø¯Ø±ÛŒÙ„', 'Ø¯Ùˆ Ù†ÙØ± Ø§Ø² ØªÛŒÙ… Ø¯Ø± Ø­Ø§Ù„ Ø§ØªØµØ§Ù„ Ùˆ Ø³ÛŒÙ…\u200cÚ©Ø´ÛŒ Ù‚Ø§Ø¨ Ø§Ù„Ù…Ø§Ù† Ú©Ù†Ø§Ø± Ø®ÛŒØ§Ø¨Ø§Ù†', 'Ù†ØµØ¨ Ø¨Ø®Ø´ÛŒ Ø§Ø² Ù‚Ø§Ø¨ Ù†ÙˆØ±Ø§Ù†ÛŒ Ø§Ù„Ù…Ø§Ù† Ø±ÙˆÛŒ Ú©Ø§Ù…ÛŒÙˆÙ†', 'ÛŒÚ©ÛŒ Ø§Ø² Ø§Ø¹Ø¶Ø§ÛŒ ØªÛŒÙ… Ù…Ù‚Ø§Ø¨Ù„ Ø§Ù„Ù…Ø§Ù† Ù†Ø¦ÙˆÙ†ÛŒ Ø¨Ø§Ø±Ú¯ÛŒØ±ÛŒ\u200cØ´Ø¯Ù‡ Ø¯Ø± Ø´Ø¨', 'Ø¨Ø§Ø±Ú¯ÛŒØ±ÛŒ Ù‚Ø§Ø¨ Ø§Ù„Ù…Ø§Ù† Ø±ÙˆÛŒ Ú©Ø§Ù…ÛŒÙˆÙ† Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„', 'Ù†ØµØ¨ Ø´Ø¨Ø§Ù†Ù‡\u200cÛŒ Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„ Ø¯Ø± Ø®ÛŒØ§Ø¨Ø§Ù†', 'Ù†ØµØ¨ Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„ Ø¨Ø± Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù† Ø¯Ø± ØºØ±ÙˆØ¨', 'Ø§Ù„Ù…Ø§Ù† Ø¢ÙˆÛŒØ®ØªÙ‡ Ø¨Ø± Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù† Ù‡Ù†Ú¯Ø§Ù… Ù†ØµØ¨ Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„', 'Ø¹Ø¶ÙˆÛŒ Ø§Ø² ØªÛŒÙ… Ú©Ù†Ø§Ø± Ø®ÛŒØ§Ø¨Ø§Ù† Ù‡Ù†Ú¯Ø§Ù… Ù†ØµØ¨ Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„', 'Ù†ØµØ¨ Ø´Ø¨Ø§Ù†Ù‡\u200cÛŒ Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„ Ø¯Ø± Ø®ÛŒØ§Ø¨Ø§Ù†ÛŒ Ø¨Ø§ Ù†Ø®Ù„', 'Ù†Ù…Ø§ÛŒ Ù†Ø²Ø¯ÛŒÚ© Ù†ØµØ¨ Ø§Ù„Ù…Ø§Ù† Ø±ÙˆÛŒ Ø³Ø¨Ø¯ Ø¨Ø§Ù„Ø§Ø¨Ø±', 'Ù†ØµØ¨ Ù†Ù‚Ø´ Ù†ÙˆØ±Ø§Ù†ÛŒ Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø³Ø¨Ø¯ Ø¨Ø§Ù„Ø§Ø¨Ø± Ø¯Ø± ØºØ±ÙˆØ¨', 'Ù†ØµØ¨ Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø³Ø¨Ø¯ Ø¨Ø§Ù„Ø§Ø¨Ø± Ú©Ø§Ù…ÛŒÙˆÙ† Ø¯Ø± Ø§Ù†ØªÙ‡Ø§ÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†', 'Ø¹Ø¶ÙˆÛŒ Ø§Ø² ØªÛŒÙ… Ù¾Ø±ØªÙˆ Ù†ÙˆØ± Ø¯Ø± Ø®ÛŒØ§Ø¨Ø§Ù† Ù…Ø­Ù„ Ø§Ø¬Ø±Ø§ Ø¯Ø± Ù†ÙˆØ± ØºØ±ÙˆØ¨', 'Ø¯Ùˆ Ù†ÙØ± Ø¯Ø± Ø®ÛŒØ§Ø¨Ø§Ù† Ø´Ø¨Ø§Ù†Ù‡ Ù¾Ø³ Ø§Ø² Ø±ÙˆØ´Ù†\u200cØ´Ø¯Ù† Ø§Ù„Ù…Ø§Ù†\u200cÙ‡Ø§']
    PRODUCT_ALTS = ['Ø±ÛŒØ³Ù‡\u200cÛŒ Ù†ÙˆØ±ÛŒ Ú¯Ù„\u200cØ¯Ø§Ø± Ùˆ Ø¯Ø§Ù†Ù‡\u200cØ¨Ø±ÙÛŒ Ø¯Ø± Ù†Ù…Ø§ÛŒ Ø¨Ø§Ù„Ø§ Ø§Ø² Ø®ÛŒØ§Ø¨Ø§Ù† Ø´Ø¨Ø§Ù†Ù‡', 'Ø±ÛŒØ³Ù‡\u200cÛŒ Ù†ÙˆØ±ÛŒ Ø¨Ø§ Ù†Ù‚Ø´ Ù…Ø§Ù‡ÛŒ Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù† Ø¯Ø± Ø´Ø¨', 'Ø±ÛŒØ³Ù‡\u200cÛŒ Ù†ÙˆØ±ÛŒ Ø³Ø¨Ø² Ø¨Ø§ Ù†Ù‚Ø´ Ø®ÙˆØ±Ø´ÛŒØ¯ Ùˆ Ù…Ø§Ù‡ Ø¯Ø± Ù…Ø±Ú©Ø²ØŒ Ø¯Ø± Ø´Ø¨']
    STAGE_TEXT = {
        "design": "Ø·Ø±Ø§Ø­ÛŒ Ù†Ù‚Ø´â€ŒÙ‡Ø§ Ùˆ Ø¨Ø§Ø²Ø¨ÛŒÙ†ÛŒ Ø·Ø±Ø­ Ø®Ø·ÛŒ Ø±ÙˆÛŒ Ù†Ù‚Ø´Ù‡ Ùˆ Ù…ÛŒØ² Ú©Ø§Ø±ØŒ Ù¾ÛŒØ´ Ø§Ø² Ø³Ø§Ø®Øª.",
        "build": "Ø³Ø§Ø®Øª Ø§Ù„Ù…Ø§Ù† Ø¨Ø§ Ø®Ø·ÙˆØ· Ù†Ø¦ÙˆÙ† Ùˆ Ø®ÙˆØ´Ù†ÙˆÛŒØ³ÛŒØŒ Ø§ØªØµØ§Ù„ Ùˆ Ø³ÛŒÙ…â€ŒÚ©Ø´ÛŒ Ùˆ Ú©Ù†ØªØ±Ù„ Ù†Ù‡Ø§ÛŒÛŒ Ù¾ÛŒØ´ Ø§Ø² Ù†ØµØ¨.",
        "install": "Ø¨Ø§Ø±Ú¯ÛŒØ±ÛŒ Ø¨Ø§ Ø¬Ø±Ø«Ù‚ÛŒÙ„ Ùˆ Ù†ØµØ¨ Ø´Ø¨Ø§Ù†Ù‡â€ŒÛŒ Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ Ø±ÙˆÛŒ Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù†.",
    }

    def _seo_polish(self):
        p = Project.objects.filter(slug="haft-khan-rostam").first()
        if p:
            if not p.seo_title:
                p.seo_title = "Ù‡ÙØªâ€ŒØ®Ø§Ù† Ø±Ø³ØªÙ…: Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ Ø´Ø§Ù‡Ù†Ø§Ù…Ù‡â€ŒØ§ÛŒ"
            if not p.seo_description:
                p.seo_description = "Ù…Ø·Ø§Ù„Ø¹Ù‡â€ŒÛŒ Ù…ÙˆØ±Ø¯ÛŒ Ù¾Ø±ÙˆÚ˜Ù‡â€ŒÛŒ Ù‡ÙØªâ€ŒØ®Ø§Ù† Ø±Ø³ØªÙ…: Ø·Ø±Ø§Ø­ÛŒØŒ Ø³Ø§Ø®Øª Ùˆ Ù†ØµØ¨ Ø´Ø¨Ø§Ù†Ù‡â€ŒÛŒ Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ Ø´Ø§Ù‡Ù†Ø§Ù…Ù‡â€ŒØ§ÛŒ Ø±ÙˆÛŒ Ø®ÛŒØ§Ø¨Ø§Ù†ØŒ Ù‡Ù…Ù‡â€ŒÛŒ Ù…Ø±Ø§Ø­Ù„ ØªÙˆØ³Ø· ØªÛŒÙ… Ù¾Ø±ØªÙˆ Ù†ÙˆØ±."
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
            story = GalleryItem.objects.filter(category__title="Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ").order_by("display_order", "id")
            for i, it in enumerate(story):
                if i < len(self.HK_ALTS) and (not it.alt_text or it.alt_text == it.title):
                    it.alt_text = self.HK_ALTS[i]; it.save(update_fields=["alt_text"])
                if it.project_id is None:
                    it.project = p; it.save(update_fields=["project"])
        prod = Product.objects.filter(slug="risheh").first()
        if prod:
            if not prod.seo_title:
                prod.seo_title = "Ø±ÛŒØ³Ù‡ Ù†ÙˆØ±ÛŒ Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù†ÛŒØ› Ø«Ø¨Øª Ø³ÙØ§Ø±Ø´ Ø§Ø² Ù¾Ø±ØªÙˆ Ù†ÙˆØ±"
            if not prod.seo_description:
                prod.seo_description = "Ø±ÛŒØ³Ù‡ Ù†ÙˆØ±ÛŒ Ø§Ø®ØªØµØ§ØµÛŒ Ù¾Ø±ØªÙˆ Ù†ÙˆØ± Ø¨Ø§ Ú©ÛŒÙÛŒØª Ù‡Ù…â€ŒØ³Ø·Ø­ Ù†Ù…ÙˆÙ†Ù‡â€ŒÙ‡Ø§ÛŒ Ø®Ø§Ø±Ø¬ÛŒØŒ Ù‚ÛŒÙ…Øª Ù…Ù†Ø§Ø³Ø¨â€ŒØªØ± Ùˆ Ù…Ù‚Ø§ÙˆÙ…Øª Ø¨Ø§Ù„Ø§ Ø¯Ø± Ø¨Ø±Ø§Ø¨Ø± Ø´Ø±Ø§ÛŒØ· Ø¢Ø¨â€ŒÙˆÙ‡ÙˆØ§ÛŒÛŒØ› ÙØ±Ù… Ø«Ø¨Øª Ø³ÙØ§Ø±Ø´ Ø¢Ù†Ù„Ø§ÛŒÙ†."
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
            for i, (t, u) in enumerate([("Ø®Ø§Ù†Ù‡", "/"), ("ÙÙ„Ø³ÙÙ‡ Ù¾Ø±ØªÙˆ Ù†ÙˆØ±", "/about/"), ("Ø¢Ø«Ø§Ø±", "/gallery/"), ("Ø±ÛŒØ³Ù‡", "/products/"),
                                        ("Ø®Ø¯Ù…Ø§Øª Ùˆ Ø±Ø§Ù‡Ú©Ø§Ø±Ù‡Ø§", "/services/"), ("Ù…Ø¬Ù„Ù‡ Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø´Ù‡Ø±ÛŒ", "/articles/"), ("ØªÙ…Ø§Ø³ Ø¨Ø§ Ù…Ø§", "/contact/")]):
                NavigationItem.objects.create(navigation=main, title=t, url=u, display_order=i)
        if not foot.items.exists():
            for i, (t, u) in enumerate([("Ø¯Ø±Ø¨Ø§Ø±Ù‡ Ù…Ø§", "/about/"), ("Ø¢Ø«Ø§Ø±", "/gallery/"), ("Ù¾Ø±ÙˆÚ˜Ù‡â€ŒÙ‡Ø§", "/projects/"), ("Ù…Ù‚Ø§Ù„Ø§Øª", "/articles/"), ("ØªÙ…Ø§Ø³", "/contact/")]):
                NavigationItem.objects.create(navigation=foot, title=t, url=u, display_order=i)

    # --------------------------------------------------------------- homepage
    def _homepage(self, reset):
        video = ASSETS / ("company_video_web.mp4" if (ASSETS / "company_video_web.mp4").exists() else "company_video.mp4")
        plan = [  # (type, order, fields, image key)
            ("hero", 0, dict(title="Ø·Ø±Ø§Ø­ÛŒØŒ Ø³Ø§Ø®Øª Ùˆ Ø§Ø¬Ø±Ø§ÛŒ Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø´Ù‡Ø±ÛŒ",
                             subtitle="Ù†ÙˆØ±Ù¾Ø±Ø¯Ø§Ø²ÛŒ Ø§Ø®ØªØµØ§ØµÛŒ Ø¨Ø±Ø§ÛŒ Ù‡Ø± Ø´Ù‡Ø±Ø› Ø§Ø² Ù†ÛŒØ§Ø²Ø³Ù†Ø¬ÛŒ ØªØ§ Ù†ØµØ¨ Ùˆ Ù¾Ø´ØªÛŒØ¨Ø§Ù†ÛŒ.",
                             cta_label="Ù…Ø´Ø§Ù‡Ø¯Ù‡ Ø¢Ø«Ø§Ø±", cta_url="/gallery/"), "luster-01"),
            ("brand_intro", 1, dict(title="Ù†ÙˆØ± Ù…Ø³Ø¦ÙˆÙ„",
                                    subtitle="Ù†ÙˆØ± Ù…Ø³Ø¦ÙˆÙ„ØŒ Ù†ÙˆØ±ÛŒ Ø§Ø³Øª Ú©Ù‡ Ø§Ø² Ø§Ù†Ø±Ú˜ÛŒ Ø¢Ú¯Ø§Ù‡ Ø§Ø³ØªØ› Ø§Ø² ØªØ§Ø±ÛŒÚ©ÛŒ Ù†Ù…ÛŒâ€ŒØªØ±Ø³Ø¯Ø› Ùˆ Ø§Ø² Ø§Ù†Ø³Ø§Ù† ÙØ±Ø§ØªØ± Ù…ÛŒâ€ŒØ§Ù†Ø¯ÛŒØ´Ø¯."), "luster-02"),
            ("differentiator", 2, {}, None),
            ("featured_projects", 3, {}, None),
            ("gallery", 4, dict(title="Ø¢Ø«Ø§Ø± Ù…Ø§ Ø¯Ø± Ø´Ù‡Ø±Ù‡Ø§", subtitle="Ø§Ø² Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ø¯Ø§Ø³ØªØ§Ù†ÛŒ ØªØ§ Ù„ÙˆØ³ØªØ±Ù‡Ø§ÛŒ Ù†ÙˆØ±ÛŒ Ø´Ù‡Ø±ÛŒ Ùˆ Ø±ÛŒØ³Ù‡â€ŒÙ‡Ø§ÛŒ Ø¹Ø±Ø¶ Ø®ÛŒØ§Ø¨Ø§Ù†ÛŒ."), None),
            ("services", 5, dict(title="Ø§Ø² Ù†Ø®Ø³ØªÛŒÙ† Ø¨Ø§Ø²Ø¯ÛŒØ¯ ØªØ§ Ù¾Ø´ØªÛŒØ¨Ø§Ù†ÛŒ"), None),
            ("product_highlight", 6, dict(cta_label="Ø«Ø¨Øª Ø³ÙØ§Ø±Ø´ Ø±ÛŒØ³Ù‡"), None),
            ("workshop", 7, {}, None),
            ("company_video", 8, dict(title="Ù¾Ø±ØªÙˆ Ù†ÙˆØ± Ø±Ø§ Ø§Ø² Ù†Ø²Ø¯ÛŒÚ© Ø¨Ø¨ÛŒÙ†ÛŒØ¯", subtitle="ÙˆÛŒØ¯ÛŒÙˆÛŒ Ù…Ø¹Ø±ÙÛŒ Ø´Ø±Ú©Øª"), None),
            ("cta", 9, dict(cta_label="Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ù…Ø´Ø§ÙˆØ±Ù‡", cta_url="/contact/#consultation"), None),
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

