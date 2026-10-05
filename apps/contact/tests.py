"""
Real Django tests for apps.contact — including a regression test for the
Phase 8 bug fix (notification email was silently going nowhere because it
used mail_admins() instead of settings.CONSULTATION_NOTIFY_EMAIL).

EXECUTION STATUS: written, not run in this sandbox (no Django install
possible — see apps/projects/tests.py header). Run with:
    python manage.py test apps.contact
"""
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ConsultationRequest, ContactMessage


class ConsultationFormTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # LocMem throttle counters otherwise leak between tests

    def _payload(self, **overrides):
        data = {
            "form_type": "consultation",
            "name": "علی رضایی",
            "phone": "09121234567",
            "email": "",
            "city": "تهران",
            "project_type": "نورپردازی شهری",
            "message": "سلام، برای یک پروژه مشاوره می‌خواهم.",
            "website": "",  # honeypot, must stay empty
        }
        data.update(overrides)
        return data

    def test_valid_submission_creates_request_and_redirects(self):
        response = self.client.post(reverse("contact:index"), self._payload())
        self.assertRedirects(response, reverse("contact:index"))
        self.assertEqual(ConsultationRequest.objects.count(), 1)

    def test_honeypot_field_rejects_bots(self):
        response = self.client.post(reverse("contact:index"), self._payload(website="http://spam.example"))
        self.assertEqual(ConsultationRequest.objects.count(), 0)

    def test_missing_required_field_does_not_save(self):
        response = self.client.post(reverse("contact:index"), self._payload(name=""))
        self.assertEqual(ConsultationRequest.objects.count(), 0)

    def test_rate_limit_blocks_after_three_submissions(self):
        for n in range(3):
            self.client.post(reverse("contact:index"), self._payload(message=f"پیام شماره {n}"))
        self.assertEqual(ConsultationRequest.objects.count(), 3)

        self.client.post(reverse("contact:index"), self._payload())
        # 4th submission within the window must be rejected, not saved.
        self.assertEqual(ConsultationRequest.objects.count(), 3)

    def test_duplicate_submission_within_window_is_not_saved_twice(self):
        payload = self._payload()
        self.client.post(reverse("contact:index"), payload)
        self.client.post(reverse("contact:index"), payload)
        self.assertEqual(
            ConsultationRequest.objects.count(), 1,
            "an identical resubmission within the duplicate window must not create a second row",
        )

    @override_settings(
        CONSULTATION_NOTIFY_EMAIL="owner@partonoor.com",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_notification_email_actually_goes_to_configured_recipient(self):
        """
        Regression test for the exact bug fixed in Phase 8: the previous
        implementation used mail_admins(), which sends to settings.ADMINS
        (never defined in this project) instead of
        settings.CONSULTATION_NOTIFY_EMAIL — so this assertion would have
        FAILED against the old code (mail.outbox would be empty).
        """
        self.client.post(reverse("contact:index"), self._payload())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("owner@partonoor.com", mail.outbox[0].to)

    @override_settings(CONSULTATION_NOTIFY_EMAIL="", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_no_email_sent_when_notify_address_not_configured(self):
        self.client.post(reverse("contact:index"), self._payload())
        self.assertEqual(len(mail.outbox), 0)


class ContactMessageFormTests(TestCase):
    def _payload(self, **overrides):
        data = {
            "form_type": "message",
            "name": "سارا احمدی",
            "phone": "",
            "email": "sara@example.com",
            "message": "سوالی درباره خدمات شما دارم.",
            "website": "",
        }
        data.update(overrides)
        return data

    def test_valid_submission_creates_message(self):
        self.client.post(reverse("contact:index"), self._payload())
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_duplicate_message_not_saved_twice(self):
        payload = self._payload()
        self.client.post(reverse("contact:index"), payload)
        self.client.post(reverse("contact:index"), payload)
        self.assertEqual(ContactMessage.objects.count(), 1)


class ContactPageAdminVisibilityTests(TestCase):
    """Ensures submitted data is actually visible/manageable in the admin,
    per spec section 27 ("Do not expose personal data publicly / admin can
    manage them") — checked here at the model/queryset level."""

    def test_consultation_requests_are_queryable_by_status(self):
        ConsultationRequest.objects.create(name="A", phone="1", status="new")
        ConsultationRequest.objects.create(name="B", phone="2", status="completed")
        self.assertEqual(ConsultationRequest.objects.filter(status="new").count(), 1)
