"""Generate the WebP / medium / thumb variants for every existing image that is missing them (idempotent)."""
import os

from django.apps import apps
from django.core.management.base import BaseCommand

from apps.core.image_pipeline import generate_image_variants, variant_path
from apps.core.signals import OPTIMIZED_IMAGE_FIELDS


class Command(BaseCommand):
    help = "Create missing WebP variants for already-uploaded images."

    def handle(self, *args, **opts):
        made = 0
        for app_label, model_name, field in OPTIMIZED_IMAGE_FIELDS:
            model = apps.get_model(app_label, model_name)
            for obj in model.objects.exclude(**{field: ""}).exclude(**{f"{field}__isnull": True}):
                f = getattr(obj, field)
                try:
                    path = f.path
                except Exception:
                    continue
                if not os.path.exists(path) or os.path.exists(variant_path(path, "-thumb")):
                    continue
                try:
                    generate_image_variants(path)
                    made += 1
                except Exception as exc:  # never abort the whole run for one bad file
                    self.stderr.write(f"{path}: {exc}")
        self.stdout.write(self.style.SUCCESS(f"Image variants created for {made} files."))
