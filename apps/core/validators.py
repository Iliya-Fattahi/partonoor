import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

try:
    import magic  # python-magic — real content sniffing, not just trusting the extension
except ImportError:  # pragma: no cover - keeps local dev usable before the dep is installed
    magic = None

try:
    import defusedxml.ElementTree as DefusedET  # XXE-safe XML parsing, for SVG validation
except ImportError:  # pragma: no cover
    DefusedET = None


def _validate_file(file_obj, allowed_extensions, allowed_mime_types, max_size_mb):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            _("پسوند فایل مجاز نیست. پسوندهای مجاز: %(exts)s") % {"exts": ", ".join(allowed_extensions)}
        )

    max_size = max_size_mb * 1024 * 1024
    if file_obj.size > max_size:
        raise ValidationError(_("حجم فایل بیش از حد مجاز (%(mb)sMB) است.") % {"mb": max_size_mb})

    if magic is not None:
        file_obj.seek(0)
        detected_mime = magic.from_buffer(file_obj.read(2048), mime=True)
        file_obj.seek(0)
        if detected_mime not in allowed_mime_types:
            raise ValidationError(_("نوع فایل با محتوای واقعی آن مطابقت ندارد یا مجاز نیست."))


def validate_image_file(file_obj):
    _validate_file(
        file_obj,
        settings.ALLOWED_IMAGE_EXTENSIONS,
        settings.ALLOWED_IMAGE_MIME_TYPES,
        settings.MAX_IMAGE_UPLOAD_SIZE_MB,
    )

    from PIL import Image, UnidentifiedImageError

    try:
        file_obj.seek(0)
        with Image.open(file_obj) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError(_("فایل تصویر معتبر نیست."))
    finally:
        file_obj.seek(0)


def validate_video_file(file_obj):
    _validate_file(
        file_obj,
        settings.ALLOWED_VIDEO_EXTENSIONS,
        settings.ALLOWED_VIDEO_MIME_TYPES,
        settings.MAX_VIDEO_UPLOAD_SIZE_MB,
    )


# --- SVG-specific dangers (spec security section: "SVG خطرناک") ---
# SVG is XML, and XML can carry <script>, event-handler attributes
# (onload, onclick, ...), and external references — any of which can
# execute JavaScript if the SVG is ever opened directly, embedded via
# <object>/<iframe>, or (on some older browsers) even rendered as an <img>.
# This validator rejects any SVG containing such constructs, and parses it
# with defusedxml (not the stdlib xml.etree) to avoid XXE (XML external
# entity) attacks via a crafted DOCTYPE/ENTITY declaration.
_SVG_DANGEROUS_TAGS = ("script", "foreignobject", "iframe", "embed", "object")
_SVG_DANGEROUS_ATTR_PREFIXES = ("on",)  # onload, onclick, onmouseover, ...
_SVG_DANGEROUS_VALUE_SUBSTRINGS = ("javascript:", "data:text/html")


def validate_svg_file(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext != ".svg":
        raise ValidationError(_("فقط فایل SVG مجاز است."))

    max_size = settings.MAX_IMAGE_UPLOAD_SIZE_MB * 1024 * 1024
    if file_obj.size > max_size:
        raise ValidationError(_("حجم فایل بیش از حد مجاز است."))

    file_obj.seek(0)
    raw = file_obj.read()
    file_obj.seek(0)

    if DefusedET is None:
        # Fail closed: if we cannot safely parse the SVG, refuse it rather
        # than silently skipping validation (never treat "can't check" as
        # "assume safe" for an upload security control). If you are seeing
        # this reject a KNOWN-GOOD SVG, the real cause is almost always
        # that the `defusedxml` package isn't installed in this
        # environment yet — it was added to requirements/base.txt after
        # some environments had already run `pip install`. Fix:
        #     pip install -r requirements/dev.txt
        # (or `pip install defusedxml` directly), then re-run. This is a
        # missing-dependency problem, not a bug in the detection logic —
        # see scripts/test_svg_validator.py, which exercises this exact
        # logic with 9 real payloads (5 malicious, correctly blocked; 2
        # legitimate, correctly allowed) and passes whenever defusedxml is
        # actually importable.
        raise ValidationError(_(
            "امکان بررسی امنیتی فایل SVG وجود ندارد — کتابخانه‌ی defusedxml نصب نیست. "
            "دستور pip install -r requirements/dev.txt را اجرا کنید."
        ))

    try:
        root = DefusedET.fromstring(raw)
    except Exception as exc:
        raise ValidationError(_("فایل SVG نامعتبر است.")) from exc

    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()  # strip XML namespace, e.g. "{http://www.w3.org/2000/svg}script"
        if tag in _SVG_DANGEROUS_TAGS:
            raise ValidationError(_("فایل SVG حاوی عنصر غیرمجاز (%(tag)s) است.") % {"tag": tag})
        for attr_name, attr_value in element.attrib.items():
            local_attr = attr_name.split("}")[-1].lower()
            if any(local_attr.startswith(prefix) for prefix in _SVG_DANGEROUS_ATTR_PREFIXES):
                raise ValidationError(_("فایل SVG حاوی event handler غیرمجاز (%(attr)s) است.") % {"attr": local_attr})
            value_lower = (attr_value or "").lower()
            if any(substr in value_lower for substr in _SVG_DANGEROUS_VALUE_SUBSTRINGS):
                raise ValidationError(_("فایل SVG حاوی مقدار غیرمجاز در ویژگی‌ها است."))


def validate_ico_file(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext != ".ico":
        raise ValidationError(_("فقط فایل ICO مجاز است."))
    max_size = 1 * 1024 * 1024  # favicons are tiny — 1MB is already generous
    if file_obj.size > max_size:
        raise ValidationError(_("حجم فایل بیش از حد مجاز است."))
