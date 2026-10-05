"""
Real Django-dependent tests for the image-variant signal wiring
(apps/core/signals.py). Kept separate from scripts/test_image_pipeline.py,
which tests the pure-Pillow pipeline logic and needs no Django — these
tests exercise the Django signal integration itself (dispatch_uid dedup,
skip-on-unrelated-save, cleanup-on-delete), which cannot be tested without
a real Django + database.

EXECUTION STATUS: written, not executed in this sandbox (no Django
install possible — see apps/projects/tests.py header). Run with:
    python manage.py test apps.core
"""
import copy
import os

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.core.image_pipeline import variant_path
from apps.core.signals import connect_image_variant_signals
from apps.core.validators import validate_ico_file, validate_svg_file
from apps.projects.models import Project, ProjectCategory

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_test_image(name="signal_test.png"):
    return SimpleUploadedFile(name, TINY_PNG, content_type="image/png")


class ImageVariantSignalTests(TestCase):
    def setUp(self):
        self.category = ProjectCategory.objects.create(title="تست")

    def test_variants_are_generated_on_create(self):
        project = Project.objects.create(
            title="پروژه سیگنال", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category,
        )
        thumb = variant_path(project.cover_image.path, "-thumb")
        self.assertTrue(os.path.exists(thumb), "expected thumbnail to be generated on create")

    def test_saving_unrelated_field_does_not_regenerate_variants(self):
        """Regression test for the Phase 6 fix: editing the title alone must
        NOT re-run the image pipeline (previously it did, on every save)."""
        project = Project.objects.create(
            title="عنوان اول", short_description="s", full_description="f",
            cover_image=make_test_image(), category=self.category,
        )
        thumb = variant_path(project.cover_image.path, "-thumb")
        first_mtime = os.path.getmtime(thumb)

        project.title = "عنوان دوم"
        project.save()

        second_mtime = os.path.getmtime(thumb)
        self.assertEqual(first_mtime, second_mtime, "thumbnail was regenerated even though the image didn't change")

    def test_replacing_image_does_regenerate_variants(self):
        project = Project.objects.create(
            title="پروژه", short_description="s", full_description="f",
            cover_image=make_test_image("first.png"), category=self.category,
        )
        old_thumb = variant_path(project.cover_image.path, "-thumb")
        self.assertTrue(os.path.exists(old_thumb))

        project.cover_image = make_test_image("second.png")
        project.save()

        new_thumb = variant_path(project.cover_image.path, "-thumb")
        self.assertNotEqual(old_thumb, new_thumb)
        self.assertTrue(os.path.exists(new_thumb), "expected new thumbnail after replacing the image")

    def test_deleting_instance_cleans_up_generated_variants(self):
        project = Project.objects.create(
            title="پروژه حذفی", short_description="s", full_description="f",
            cover_image=make_test_image("to_delete.png"), category=self.category,
        )
        thumb = variant_path(project.cover_image.path, "-thumb")
        medium = variant_path(project.cover_image.path, "-medium")
        full = variant_path(project.cover_image.path, "")
        self.assertTrue(os.path.exists(thumb))

        project.delete()

        self.assertFalse(os.path.exists(thumb), "generated thumb should be cleaned up after delete")
        self.assertFalse(os.path.exists(medium), "generated medium should be cleaned up after delete")
        self.assertFalse(os.path.exists(full), "generated full webp should be cleaned up after delete")

    def test_signal_connected_exactly_once_per_model_field(self):
        """Regression test for the dispatch_uid fix: even if
        connect_image_variant_signals() is called twice (simulating a
        double app-ready edge case), the receiver list for post_save on
        Project must not contain duplicate entries."""
        connect_image_variant_signals()  # call again on purpose
        connect_image_variant_signals()

        from django.db.models.signals import post_save
        # A simple, portable assertion: connecting twice must not double the
        # number of live receivers attached to Project's post_save.
        live_count = len(post_save._live_receivers(sender=Project))
        connect_image_variant_signals()
        live_count_after_third_call = len(post_save._live_receivers(sender=Project))
        self.assertEqual(
            live_count, live_count_after_third_call,
            "calling connect_image_variant_signals() again created duplicate receivers "
            "(dispatch_uid is not preventing re-connection)",
        )


class SVGFaviconSecurityTests(TestCase):
    """
    Regression tests for the Phase 9 security fix: favicon_svg/favicon_ico
    on SiteSettings previously had NO validators at all, meaning an SVG
    containing <script>, an event handler, or an XXE payload could be
    uploaded as the site favicon. See scripts/test_svg_validator.py for
    the non-Django version of these same assertions (which actually runs
    in this sandbox, since it needs only defusedxml).
    """

    def test_svg_with_script_tag_is_rejected(self):
        malicious = SimpleUploadedFile(
            "favicon.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            content_type="image/svg+xml",
        )
        with self.assertRaises(ValidationError):
            validate_svg_file(malicious)

    def test_svg_with_event_handler_is_rejected(self):
        malicious = SimpleUploadedFile(
            "favicon.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>',
            content_type="image/svg+xml",
        )
        with self.assertRaises(ValidationError):
            validate_svg_file(malicious)

    def test_svg_with_xxe_payload_is_rejected(self):
        malicious = SimpleUploadedFile(
            "favicon.svg",
            b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>',
            content_type="image/svg+xml",
        )
        with self.assertRaises(ValidationError):
            validate_svg_file(malicious)

    def test_legitimate_svg_is_accepted(self):
        safe = SimpleUploadedFile(
            "favicon.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>',
            content_type="image/svg+xml",
        )
        try:
            validate_svg_file(safe)
        except ValidationError:
            self.fail("validate_svg_file rejected a legitimate SVG (false positive)")

    def test_non_svg_extension_is_rejected(self):
        wrong_ext = SimpleUploadedFile("favicon.png", b"not really svg", content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_svg_file(wrong_ext)

    def test_ico_wrong_extension_is_rejected(self):
        wrong_ext = SimpleUploadedFile("favicon.exe", b"MZ\x90\x00", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_ico_file(wrong_ext)

    def test_ico_correct_extension_is_accepted(self):
        valid = SimpleUploadedFile("favicon.ico", b"\x00\x00\x01\x00", content_type="image/x-icon")
        try:
            validate_ico_file(valid)
        except ValidationError:
            self.fail("validate_ico_file rejected a correctly-named .ico file")


class DjangoContextCompatShimTests(TestCase):
    """
    Regression test for the reported production error:
        AttributeError: 'super' object has no attribute 'dicts' ...
    raised by Django's own {% submit_row %} admin tag on Python 3.14.6 +
    Django 5.0.14. See apps/core/django_compat.py for the full diagnosis.

    EXECUTION STATUS: written, not run in this sandbox (no Django
    install possible here). This test exercises the actual Django
    Context class (not a fake stand-in), so once run for real
    (`python manage.py test apps.core.DjangoContextCompatShimTests`) it
    gives a genuine signal on whichever Python/Django combination it's
    run against.
    """

    def test_context_copy_does_not_raise_and_preserves_dicts(self):
        from django.template import Context

        ctx = Context({"page": "admin"})
        duplicate = copy.copy(ctx)  # this is exactly what {% submit_row %} triggers internally

        self.assertIsNot(duplicate, ctx)
        self.assertEqual(duplicate.dicts, ctx.dicts)

        duplicate.dicts.append({"extra": True})
        self.assertNotEqual(ctx.dicts, duplicate.dicts, "mutating the duplicate must not affect the original")

    def test_admin_add_view_renders_without_context_copy_error(self):
        """
        The most direct regression test: actually GET a real Django admin
        add page (Project) and confirm it renders 200, not a 500 from the
        exact AttributeError reported.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin_user = User.objects.create_superuser("admin_test", "admin@test.local", "testpass123")
        self.client.force_login(admin_user)

        response = self.client.get("/admin/projects/project/add/")
        self.assertEqual(
            response.status_code, 200,
            "Admin add view failed to render — if this fails with a 500 mentioning "
            "'super' object has no attribute 'dicts', the compat shim in "
            "apps/core/django_compat.py did not take effect (check it ran during app startup).",
        )
