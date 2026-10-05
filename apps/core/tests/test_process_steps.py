"""
Tests for ProcessStep (CMS-editable homepage workflow).
NOT EXECUTED in the authoring sandbox. Run: python manage.py test apps.core.tests.test_process_steps
"""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.core.models import HomepageSection, ProcessStep


class ProcessStepTests(TestCase):
    def setUp(self):
        call_command("seed_real_media", verbosity=0)

    def test_seed_creates_the_eight_real_workflow_steps_in_order(self):
        titles = list(ProcessStep.objects.filter(published=True).values_list("title", flat=True))
        self.assertEqual(titles[0], "نیازسنجی")
        self.assertEqual(titles[-1], "پشتیبانی")
        self.assertEqual(len(titles), 8)

    def test_unpublished_step_is_excluded_from_homepage(self):
        ProcessStep.objects.filter(title="ساخت").update(published=False)
        HomepageSection.objects.filter(section_type="differentiator").update(is_visible=True)
        content = self.client.get(reverse("home")).content.decode("utf-8")
        self.assertIn("نیازسنجی", content)
        self.assertNotIn("<div><h3>ساخت</h3><p>", content)  # step markup only; the services list also has a «ساخت» h3
