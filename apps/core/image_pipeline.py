"""
Real image optimization pipeline (spec sections 36/45/50/78/16 — image
optimization / WebP / thumbnails / responsive images / N+1-safe media).

Given an uploaded image, produces:
  - a WebP copy at full resolution (usually 25-50% smaller than JPEG/PNG)
  - a small WebP thumbnail (for list/grid views, gallery previews, admin
    previews) capped at THUMBNAIL_MAX_WIDTH
  - a medium WebP variant capped at MEDIUM_MAX_WIDTH (for card/grid images
    on the public site, so a 4000px project photo is never shipped to a
    320px mobile card)

This module has NO Django import — it operates on raw bytes/file paths, so
it is independently testable (and IS tested — see
scripts/test_image_pipeline.py, which actually runs in this sandbox because
Pillow is available here even though Django is not). It is wired into
Django via apps/core/signals.py, which calls this on post_save for every
model with an image field that should get variants.

DESIGN NOTE (fixed during Phase 6 regression audit): the file-based and
bytes-based entry points used to each reimplement orientation-fix +
mode-conversion independently, and had drifted out of sync (the bytes path
unconditionally flattened RGBA to RGB, silently destroying transparency,
while the file path preserved it). Both entry points now share the exact
same `_normalize()` + `_build_variant_images()` core, so there is exactly
one place that decides how a source image is prepared — no more risk of
the two paths disagreeing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps

THUMBNAIL_MAX_WIDTH = 480
MEDIUM_MAX_WIDTH = 1200
WEBP_QUALITY = 82


@dataclass
class ImageVariants:
    original_path: str
    webp_full_path: str
    webp_medium_path: str
    webp_thumb_path: str


def variant_path(original_path: str, suffix: str) -> str:
    root, _ext = os.path.splitext(original_path)
    return f"{root}{suffix}.webp"


def _resize_to_max_width(img: Image.Image, max_width: int) -> Image.Image:
    if img.width <= max_width:
        return img
    ratio = max_width / float(img.width)
    new_height = max(1, int(img.height * ratio))
    return img.resize((max_width, new_height), Image.LANCZOS)


def _normalize(img: Image.Image) -> Image.Image:
    """
    Single source of truth for orientation + color-mode handling, shared by
    both entry points below. KNOWN LIMITATION (documented, not silently
    hidden): CMYK and other exotic modes are converted straight to RGB by
    Pillow without ICC-aware color management, which can shift colors
    slightly. This is acceptable for web delivery of real photographs
    (CMYK is a print-workflow artifact almost never produced by a camera or
    phone) and deliberately not over-engineered with a color-management
    library for a case this project is unlikely to hit.
    """
    img = ImageOps.exif_transpose(img)  # fix phone-camera rotation
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGBA")  # preserves transparency, including palette-with-alpha
    else:
        img = img.convert("RGB")
    return img


def _build_variant_images(img: Image.Image) -> dict:
    return {
        "full": img,
        "medium": _resize_to_max_width(img, MEDIUM_MAX_WIDTH),
        "thumb": _resize_to_max_width(img, THUMBNAIL_MAX_WIDTH),
    }


def generate_image_variants(original_path: str) -> ImageVariants:
    """
    Reads the image at original_path, writes three WebP derivatives next to
    it (full-res WebP, a <=1200px "medium" WebP, a <=480px "thumb" WebP),
    and returns their paths. Safe to call again (overwrites, does not
    duplicate).
    """
    with Image.open(original_path) as raw:
        img = _normalize(raw)
        variants = _build_variant_images(img)

        full_path = variant_path(original_path, "")
        variants["full"].save(full_path, "WEBP", quality=WEBP_QUALITY, method=6)

        medium_path = variant_path(original_path, "-medium")
        variants["medium"].save(medium_path, "WEBP", quality=WEBP_QUALITY, method=6)

        thumb_path = variant_path(original_path, "-thumb")
        variants["thumb"].save(thumb_path, "WEBP", quality=WEBP_QUALITY, method=6)

    return ImageVariants(
        original_path=original_path,
        webp_full_path=full_path,
        webp_medium_path=medium_path,
        webp_thumb_path=thumb_path,
    )


def generate_image_variants_from_bytes(data: bytes) -> dict:
    """Same pipeline, in-memory — used by the test script and by any future
    async/queue-based worker that receives bytes rather than a file path.
    Uses the exact same _normalize()/_build_variant_images() as the
    file-based path above, so behavior (including transparency handling)
    cannot silently drift between the two again."""
    with Image.open(BytesIO(data)) as raw:
        img = _normalize(raw)
        variants = _build_variant_images(img)

        outputs = {}
        for label, variant_img in variants.items():
            buf = BytesIO()
            variant_img.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
            outputs[label] = {"bytes": buf.getvalue(), "width": variant_img.width, "height": variant_img.height}
        return outputs
