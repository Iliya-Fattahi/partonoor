"""
Wires apps.core.image_pipeline into Django via pre_save/post_save/post_delete
signals, so every image uploaded through any admin form automatically gets
WebP + medium + thumb variants generated on disk next to the original.

Connected in apps/core/apps.py CoreConfig.ready().

--- Regression-audit notes (read before changing this file) ---

1. No infinite loop: generate_image_variants() only writes NEW sibling
   files directly to disk via PIL — it never calls instance.save() or
   touches any model field, so it cannot re-trigger post_save on the same
   or any other model. The generated .webp files are plain files on disk,
   never Django model instances, so they never fire signals themselves.

2. Duplicate connection guarded by dispatch_uid: without a stable
   dispatch_uid, Django's signal dispatcher cannot detect that the same
   receiver was already connected, so if CoreConfig.ready() ever runs more
   than once in the same process (this happens in some test-runner /
   autoreload edge cases), post_save.connect() would silently connect the
   SAME receiver a second time — meaning every save reprocesses the image
   twice. Each connect() call below now passes a unique, stable
   dispatch_uid, so Django deduplicates automatically.

3. Reprocessing avoided on unrelated saves: previously, saving a Project
   just to fix a typo in the title re-ran the full image pipeline every
   time, because post_save fired unconditionally regardless of whether the
   image field actually changed. A pre_save receiver now records the
   previous file path (if any) on the instance; post_save only regenerates
   variants when that path actually changed, OR when the expected
   thumbnail is missing on disk (self-healing after e.g. a manual media
   restore that didn't include generated variants).

4. Cleanup on delete: post_delete removes the *generated* WebP variants
   (never the original — Django's own convention is that deleting a model
   instance does not delete its FileField's underlying file, and changing
   that default is a separate decision this phase does not make).

5. Defense-in-depth against path traversal: Django's Storage layer already
   sanitizes uploaded filenames (get_valid_name strips path separators and
   ".."), so image_field.path is already safe by the time it reaches this
   code. _assert_within_media_root() below is an extra, cheap safety net —
   if a future storage backend or manual DB edit ever produces a path
   outside MEDIA_ROOT, we refuse to process it rather than silently write
   files somewhere unexpected.
"""
import logging
import os

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save

from .image_pipeline import variant_path, generate_image_variants

logger = logging.getLogger("apps.core.image_variants")

# (app_label, model_name, image_field_name) for every model with an image
# that should get optimized derivatives. Kept as one explicit list rather
# than introspecting every ImageField automatically — brand/SEO images are
# deliberately excluded (they're small, few, and often need pixel-perfect
# control e.g. the favicon/logo), matching spec section 4's instruction not
# to reprocess the official brand symbol.
OPTIMIZED_IMAGE_FIELDS = [
    ("projects", "Project", "cover_image"),
    ("projects", "ProjectImage", "image"),
    ("services", "Service", "main_image"),
    ("services", "ServiceImage", "image"),
    ("products", "Product", "main_image"),
    ("products", "ProductImage", "image"),
    ("articles", "Article", "cover_image"),
    ("gallery", "GalleryItem", "image"),
    ("company", "TeamMember", "photo"),
    ("company", "AboutSection", "image"),
    ("company", "WorkshopSection", "image"),
    ("core", "HomepageSection", "image"),
]

# Attribute name used to stash the pre-save path on the instance between
# pre_save and post_save (per field, so multiple optimized fields on the
# same instance — none currently, but future-proof — don't clobber each other).
_PRE_SAVE_ATTR = "_partonoor_prev_image_path__{field}"


def _assert_within_media_root(path: str) -> bool:
    media_root = os.path.realpath(settings.MEDIA_ROOT)
    real_path = os.path.realpath(path)
    return os.path.commonpath([media_root, real_path]) == media_root


def _make_pre_save_receiver(field_name: str):
    def _receiver(sender, instance, **kwargs):
        prev_path = None
        if instance.pk:
            try:
                old_instance = sender.objects.get(pk=instance.pk)
                old_field = getattr(old_instance, field_name, None)
                if old_field and getattr(old_field, "name", None):
                    prev_path = old_field.path
            except (sender.DoesNotExist, ValueError, NotImplementedError):
                prev_path = None
        setattr(instance, _PRE_SAVE_ATTR.format(field=field_name), prev_path)

    return _receiver


def _make_post_save_receiver(field_name: str):
    def _receiver(sender, instance, **kwargs):
        image_field = getattr(instance, field_name, None)
        if not image_field or not getattr(image_field, "name", None):
            return

        try:
            path = image_field.path  # only works for local FileSystemStorage
        except (NotImplementedError, ValueError):
            logger.info(
                "Skipping variant generation for %s.%s — storage backend has no local path "
                "(expected for remote storage e.g. S3; wire a storage-aware variant of "
                "generate_image_variants there instead).",
                sender.__name__, field_name,
            )
            return

        if not _assert_within_media_root(path):
            logger.error(
                "Refusing to process %s.%s — resolved path %s is outside MEDIA_ROOT.",
                sender.__name__, field_name, path,
            )
            return

        prev_path = getattr(instance, _PRE_SAVE_ATTR.format(field=field_name), None)
        thumb_path = variant_path(path, "-thumb")
        already_has_variants = os.path.exists(thumb_path)

        if prev_path == path and already_has_variants:
            return  # image field didn't change AND variants already exist — nothing to do

        try:
            generate_image_variants(path)
        except Exception:
            # Never let a thumbnailing failure break the actual save — but
            # log loudly so it surfaces in production logs (spec section 54).
            logger.exception("Image variant generation failed for %s.%s (%s)", sender.__name__, field_name, path)

    return _receiver


def _make_post_delete_receiver(field_name: str):
    def _receiver(sender, instance, **kwargs):
        image_field = getattr(instance, field_name, None)
        if not image_field or not getattr(image_field, "name", None):
            return
        try:
            path = image_field.path
        except (NotImplementedError, ValueError):
            return
        for suffix in ("", "-medium", "-thumb"):
            variant_file_path = variant_path(path, suffix)
            if os.path.exists(variant_file_path):
                try:
                    os.remove(variant_file_path)
                except OSError:
                    logger.exception("Failed to remove generated variant %s", variant_file_path)

    return _receiver


def connect_image_variant_signals():
    from django.apps import apps as django_apps

    for app_label, model_name, field_name in OPTIMIZED_IMAGE_FIELDS:
        try:
            model = django_apps.get_model(app_label, model_name)
        except LookupError:
            continue

        uid_base = f"partonoor_image_variants_{app_label}_{model_name}_{field_name}"
        pre_save.connect(
            _make_pre_save_receiver(field_name), sender=model,
            weak=False, dispatch_uid=f"{uid_base}_pre_save",
        )
        post_save.connect(
            _make_post_save_receiver(field_name), sender=model,
            weak=False, dispatch_uid=f"{uid_base}_post_save",
        )
        post_delete.connect(
            _make_post_delete_receiver(field_name), sender=model,
            weak=False, dispatch_uid=f"{uid_base}_post_delete",
        )


def _invalidate_site_settings_cache(sender, **kwargs):
    from django.core.cache import cache
    from apps.core.middleware import CACHE_KEY
    cache.delete(CACHE_KEY)


def _invalidate_navigation_cache(sender, **kwargs):
    from django.core.cache import cache
    from apps.core.context_processors import NAV_CACHE_KEY
    cache.delete(NAV_CACHE_KEY)


def connect_cache_invalidation_signals():
    """
    Ensures admin edits to SiteSettings or Navigation/NavigationItem are
    visible immediately, not after the cache TTL expires. Without this, an
    editor changing e.g. the phone number or a menu item would have to wait
    up to 15 minutes (the fallback TTL) to see it live — exactly the
    staleness problem explicitly flagged during the Phase 12 review.
    """
    from apps.core.models import Navigation, NavigationItem, SiteSettings

    post_save.connect(
        _invalidate_site_settings_cache, sender=SiteSettings,
        weak=False, dispatch_uid="partonoor_invalidate_site_settings_cache_save",
    )

    for model in (Navigation, NavigationItem):
        post_save.connect(
            _invalidate_navigation_cache, sender=model,
            weak=False, dispatch_uid=f"partonoor_invalidate_nav_cache_save_{model.__name__}",
        )
        post_delete.connect(
            _invalidate_navigation_cache, sender=model,
            weak=False, dispatch_uid=f"partonoor_invalidate_nav_cache_delete_{model.__name__}",
        )
