"""
KYC file validators.

Two distinct validators:
  1. validate_document_file  — for all standard documents (CNI, location plan, NIU)
  2. validate_passport_photo — for passport photos specifically, adds dimension
                               and aspect ratio checks on top of standard validation

All validators are plain functions — no coupling to models or serializers.
This makes them independently testable and reusable anywhere in the codebase.

Security layering (applies to all files):
  Layer 1 — File size check
  Layer 2 — Extension check
  Layer 3 — Magic bytes check (python-magic reads actual file content)
  Layer 4 — Extension vs detected MIME consistency check

Passport photo adds:
  Layer 5 — Minimum resolution check
  Layer 6 — Aspect ratio check (must be portrait, ~3:4 ratio)
"""

import os

import magic
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image


# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_MIME_TYPES = getattr(
    settings,
    "ALLOWED_DOCUMENT_MIME_TYPES",
    ["application/pdf", "image/jpeg", "image/png"],
)

ALLOWED_EXTENSIONS = getattr(
    settings,
    "ALLOWED_DOCUMENT_EXTENSIONS",
    [".pdf", ".jpg", ".jpeg", ".png"],
)

MIME_TO_EXTENSIONS = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Passport photo constants
# Standard passport photo dimensions: 35mm x 45mm
# At 300 DPI that is approximately 413 x 531 pixels minimum
PASSPORT_MIN_WIDTH_PX = 300
PASSPORT_MIN_HEIGHT_PX = 400

# Aspect ratio tolerance — passport photos are roughly 3:4 (width:height)
# We allow a 15% tolerance around this ratio to account for slight variations
# e.g. 35x45mm = 0.777 ratio, 2x2 inch = 1.0 ratio (US standard)
# We support both by allowing 0.65 to 1.05
PASSPORT_MIN_RATIO = 0.65
PASSPORT_MAX_RATIO = 1.05

# Passport photos must be images — PDFs not accepted
PASSPORT_ALLOWED_MIME_TYPES = ["image/jpeg", "image/png"]
PASSPORT_ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png"]
PASSPORT_MIME_TO_EXTENSIONS = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
}


# ── Standard document validator ───────────────────────────────────────────────

def validate_document_file(file) -> None:
    """
    Validates any standard KYC document (CNI, location plan, NIU doc).
    Accepts PDF, JPEG, PNG up to 10MB.
    Raises django.core.exceptions.ValidationError on failure.
    """
    _validate_file_size(file, MAX_FILE_SIZE_BYTES)
    _validate_extension(file, ALLOWED_EXTENSIONS)
    detected_mime = _validate_magic_bytes(file, ALLOWED_MIME_TYPES)
    _validate_extension_matches_mime(file, detected_mime, MIME_TO_EXTENSIONS)


# ── Passport photo validator ──────────────────────────────────────────────────

def validate_passport_photo(file) -> None:
    """
    Validates a passport photo file.

    Runs all standard checks first, then adds:
    - Must be an image (no PDFs)
    - Minimum resolution: 300x400 pixels
    - Aspect ratio: between 0.65 and 1.05 (width/height)
      This accepts standard passport formats from multiple countries
      while rejecting landscape photos, wide selfies, and full-body images.

    Raises django.core.exceptions.ValidationError on failure.
    """
    _validate_file_size(file, MAX_FILE_SIZE_BYTES)
    _validate_extension(file, PASSPORT_ALLOWED_EXTENSIONS)
    detected_mime = _validate_magic_bytes(file, PASSPORT_ALLOWED_MIME_TYPES)
    _validate_extension_matches_mime(file, detected_mime, PASSPORT_MIME_TO_EXTENSIONS)
    _validate_passport_dimensions(file)


# ── Shared low-level checks ───────────────────────────────────────────────────

def _validate_file_size(file, max_bytes: int) -> None:
    if file.size > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise ValidationError(f"File size must not exceed {max_mb} MB.")


def _validate_extension(file, allowed_extensions: list) -> None:
    _, ext = os.path.splitext(file.name.lower())
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(allowed_extensions)}."
        )


def _validate_magic_bytes(file, allowed_mimes: list) -> str:
    """
    Reads the first 2048 bytes to detect true file type.
    Always rewinds the file pointer after reading.
    Returns the detected MIME type string.
    """
    file.seek(0)
    header = file.read(2048)
    file.seek(0)

    detected_mime = magic.from_buffer(header, mime=True)

    if detected_mime not in allowed_mimes:
        raise ValidationError(
            f"File content does not match an allowed type. "
            f"Detected: '{detected_mime}'."
        )

    return detected_mime


def _validate_extension_matches_mime(
    file, detected_mime: str, mime_to_extensions: dict
) -> None:
    """
    Ensures the file extension is consistent with detected MIME type.
    Catches files like: a real JPEG submitted with a .pdf extension.
    """
    _, ext = os.path.splitext(file.name.lower())
    allowed_exts = mime_to_extensions.get(detected_mime, [])

    if ext not in allowed_exts:
        raise ValidationError(
            f"File extension '{ext}' does not match the detected "
            f"file type '{detected_mime}'. "
            f"Expected: {', '.join(allowed_exts)}."
        )


def _validate_passport_dimensions(file) -> None:
    """
    Validates passport photo dimensions and aspect ratio using Pillow.

    Checks:
    1. Minimum width and height in pixels
    2. Aspect ratio (width/height) must be within portrait range

    Rewinds file pointer before and after reading so subsequent
    operations (e.g. saving to disk) work correctly.
    """
    file.seek(0)

    try:
        image = Image.open(file)
        image.verify()  # detects truncated or corrupt images
    except Exception:
        raise ValidationError(
            "The passport photo could not be read. "
            "Please upload a valid JPEG or PNG image."
        )

    # Re-open after verify() — Pillow requires this because
    # verify() exhausts the file object internally
    file.seek(0)
    image = Image.open(file)
    width, height = image.size
    file.seek(0)

    # Minimum resolution check
    if width < PASSPORT_MIN_WIDTH_PX or height < PASSPORT_MIN_HEIGHT_PX:
        raise ValidationError(
            f"Passport photo resolution is too low ({width}x{height}px). "
            f"Minimum required: {PASSPORT_MIN_WIDTH_PX}x{PASSPORT_MIN_HEIGHT_PX}px. "
            f"Please use a higher quality photo."
        )

    # Aspect ratio check
    ratio = width / height
    if not (PASSPORT_MIN_RATIO <= ratio <= PASSPORT_MAX_RATIO):
        raise ValidationError(
            f"Passport photo dimensions are not valid (ratio: {ratio:.2f}). "
            f"The photo must be portrait-oriented with roughly equal width and height. "
            f"Full-body photos, landscape photos, and wide selfies are not accepted."
        )