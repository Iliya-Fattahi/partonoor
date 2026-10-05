from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import ConsultationRequestForm, ContactMessageForm
from .models import ConsultationRequest, ContactMessage

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_SUBMISSIONS = 3

# How recently an identical submission must have arrived to be treated as an
# accidental double-click / resubmit rather than a genuinely new request
# (spec section 11: "duplicate submission handling").
DUPLICATE_SUBMISSION_WINDOW = timedelta(minutes=2)


def _rate_limited(request, form_key):
    """Simple cache-based throttle — no extra infra required."""
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"contact_throttle:{form_key}:{ip}"
    count = cache.get(cache_key, 0)
    if count >= RATE_LIMIT_MAX_SUBMISSIONS:
        return True
    cache.set(cache_key, count + 1, RATE_LIMIT_WINDOW_SECONDS)
    return False


def _is_duplicate_consultation(name, phone, message):
    cutoff = timezone.now() - DUPLICATE_SUBMISSION_WINDOW
    return ConsultationRequest.objects.filter(
        name=name, phone=phone, message=message, created_at__gte=cutoff,
    ).exists()


def _is_duplicate_message(name, phone, email, message):
    cutoff = timezone.now() - DUPLICATE_SUBMISSION_WINDOW
    return ContactMessage.objects.filter(
        name=name, phone=phone, email=email, message=message, created_at__gte=cutoff,
    ).exists()


def _notify(subject, body):
    """
    Sends a plain notification email to the configured recipient. Previous
    version of this function called mail_admins(), which sends to
    settings.ADMINS — a setting this project never defines — so the
    notification silently never went anywhere regardless of
    CONSULTATION_NOTIFY_EMAIL being set. Fixed to actually address the
    configured recipient directly.
    """
    if not settings.CONSULTATION_NOTIFY_EMAIL:
        return
    send_mail(
        subject=subject,
        message=body,
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[settings.CONSULTATION_NOTIFY_EMAIL],
        fail_silently=True,
    )


def contact_view(request):
    consultation_form = ConsultationRequestForm()
    contact_form = ContactMessageForm()

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "consultation":
            consultation_form = ConsultationRequestForm(request.POST)
            if _rate_limited(request, "consultation"):
                messages.error(request, "درخواست‌های زیادی ارسال شده است. کمی بعد دوباره تلاش کنید.")
            elif consultation_form.is_valid():
                cd = consultation_form.cleaned_data
                if _is_duplicate_consultation(cd["name"], cd["phone"], cd.get("message", "")):
                    # Treat as success from the user's point of view (they
                    # likely double-clicked submit) — don't create a second row.
                    messages.success(request, "درخواست شما قبلاً ثبت شده است. به‌زودی با شما تماس می‌گیریم.")
                else:
                    consultation_form.save()
                    _notify(
                        "درخواست مشاوره جدید — پرتو نور",
                        f"نام: {cd['name']}\nتلفن: {cd['phone']}\nشهر: {cd.get('city', '')}\n"
                        f"نوع پروژه: {cd.get('project_type', '')}\nپیام: {cd.get('message', '')}",
                    )
                    messages.success(request, "درخواست شما با موفقیت ثبت شد. به‌زودی با شما تماس می‌گیریم.")
                return redirect("contact:index")

        elif form_type == "message":
            contact_form = ContactMessageForm(request.POST)
            if _rate_limited(request, "message"):
                messages.error(request, "پیام‌های زیادی ارسال شده است. کمی بعد دوباره تلاش کنید.")
            elif contact_form.is_valid():
                cd = contact_form.cleaned_data
                if _is_duplicate_message(cd["name"], cd.get("phone", ""), cd.get("email", ""), cd["message"]):
                    messages.success(request, "پیام شما قبلاً ثبت شده است.")
                else:
                    contact_form.save()
                    _notify(
                        "پیام تماس جدید — پرتو نور",
                        f"نام: {cd['name']}\nتلفن: {cd.get('phone', '')}\nایمیل: {cd.get('email', '')}\n"
                        f"پیام: {cd['message']}",
                    )
                    messages.success(request, "پیام شما با موفقیت ارسال شد.")
                return redirect("contact:index")

    from apps.core.seo import build_seo
    seo = build_seo(
        request,
        title="تماس با ما و درخواست مشاوره نورپردازی",
        description="با پرتو نور تماس بگیرید: درخواست مشاوره برای طراحی، ساخت و اجرای المان نوری شهری، اطلاعات تماس و فرم ارسال پیام.",
        crumbs=[("خانه", "/"), ("تماس با ما", None)],
    )
    return render(request, "contact/contact.html", {
        "seo": seo, "breadcrumb_items": seo["breadcrumb_items"],
        "consultation_form": consultation_form,
        "contact_form": contact_form,
    })
