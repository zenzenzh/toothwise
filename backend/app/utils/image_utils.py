import uuid
from pathlib import Path
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.config import get_settings

settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Canonical extension derived from PIL's own detected format, never from
# the client-supplied filename - see the validation step below.
_FORMAT_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

# Hard ceiling on pixel dimensions. Rejects decompression-bomb style
# uploads (a tiny file that decodes into a gigantic bitmap and exhausts
# memory/CPU) before any resizing or model inference touches it.
MAX_DIMENSION_PX = 6000


def _validate_and_decode(contents: bytes) -> tuple[Image.Image, str]:
    """
    The real security boundary, shared by every upload path in this
    module: attempt to decode the actual bytes as an image BEFORE
    anything touches disk or a model. A renamed executable or arbitrary
    blob with a spoofed image/* header fails here and is rejected before
    it's written anywhere. img.verify() checks structural integrity; a
    second open() is needed afterwards since verify() leaves the file
    object unusable for further reads (Pillow's documented pattern).

    Returns a decoded, re-encodable PIL.Image plus its detected format.
    Callers that persist the bytes (save_upload) re-save from this
    decoded image rather than writing the original bytes verbatim, so
    anything PIL didn't need to render the image - trailing/appended data
    (polyglot files), embedded scripts in metadata, EXIF payloads - is
    discarded, since only the pixel grid survives a decode round trip.
    """
    try:
        with Image.open(BytesIO(contents)) as probe:
            probe.verify()
        img = Image.open(BytesIO(contents))
        img.load()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image.",
        )

    if img.width > MAX_DIMENSION_PX or img.height > MAX_DIMENSION_PX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image dimensions exceed the {MAX_DIMENSION_PX}px limit.",
        )
    if getattr(img, "n_frames", 1) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Animated images are not accepted.",
        )
    return img, img.format


def _read_and_check_content_type(file: UploadFile, max_mb: int) -> bytes:
    # First check: the browser/client-reported Content-Type header. This
    # is attacker-controlled and easily spoofed, so it's a cheap early
    # reject for the common case, NOT the real security boundary - that's
    # _validate_and_decode() above, which actually parses the bytes.
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG or WEBP images are accepted.",
        )
    contents = file.file.read()
    max_bytes = max_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds the {max_mb}MB limit.",
        )
    return contents




def save_upload(file: UploadFile, patient_id: int) -> tuple[str, int, int]:
    contents = _read_and_check_content_type(file, settings.MAX_UPLOAD_MB)
    img, pil_format = _validate_and_decode(contents)
    width, height = img.size

    clean_buffer = BytesIO()
    save_kwargs = {}
    if pil_format == "JPEG":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        save_kwargs = {"quality": 92}
    elif pil_format == "WEBP":
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")
        save_kwargs = {"quality": 92}
    img.save(clean_buffer, format=pil_format, **save_kwargs)
    contents = clean_buffer.getvalue()

    ext = _FORMAT_EXTENSIONS.get(pil_format, ".jpg")

    upload_dir = Path(settings.UPLOAD_DIR) / "screenings"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"patient{patient_id}_{uuid.uuid4().hex[:10]}{ext}"
    dest = upload_dir / filename

    with open(dest, "wb") as f:
        f.write(contents)

    # image_path is stored relative to UPLOAD_DIR (e.g.
    # "screenings/xxx.webp"). It's served exclusively through the
    # authenticated GET /screenings/{id}/image and
    # /screenings/self/{id}/image endpoints (app/routers/screenings.py),
    # which resolve this relative path back under UPLOAD_DIR and check
    # ownership before returning the file - there is no public static
    # file mount for uploads.
    relative_path = dest.relative_to(settings.UPLOAD_DIR)
    return str(relative_path).replace("\\", "/"), width, height
