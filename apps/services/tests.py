"""
Real Django tests for the services app. EXECUTION STATUS: written, not run
in this sandbox (no Django install possible — see apps/projects/tests.py).
Run with: python manage.py test apps.services
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Service

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_test_image(name="s.png"):
    return SimpleUploadedFile(name, TINY_PNG, content_type="image/png")


class ServiceViewTests(TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            title="طراحی نورپردازی شهری", short_description="s", full_description="f",
            main_image=make_test_image(), published=True,
        )

    def test_list_returns_200(self):
        self.assertEqual(self.client.get(reverse("services:list")).status_code, 200)

    def test_list_hides_unpublished(self):
        Service.objects.create(
            title="خدمت منتشرنشده", short_description="s", full_description="f",
            main_image=make_test_image("x.png"), published=False,
        )
        response = self.client.get(reverse("services:list"))
        titles = [s.title for s in response.context["services"]]
        self.assertNotIn("خدمت منتشرنشده", titles)

    def test_detail_returns_200_for_published(self):
        response = self.client.get(self.service.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_detail_returns_404_for_unpublished(self):
        self.service.published = False
        self.service.save()
        self.assertEqual(self.client.get(self.service.get_absolute_url()).status_code, 404)

    def test_slug_auto_generated(self):
        self.assertTrue(self.service.slug)
