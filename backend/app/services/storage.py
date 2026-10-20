"""Local image storage with strict validation (type checked from file bytes, size
limit, random file names). Kept behind small functions so a cloud bucket can
replace it later."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError

_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def sniff_image_type(head: bytes) -> str | None:
    for ctype, sigs in _SIGNATURES.items():
        if any(head.startswith(s) for s in sigs):
            return ctype
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


async def save_property_image(property_id: uuid.UUID, upload: UploadFile) -> tuple[str, str]:
    """Validate and store an image. Returns (relative storage path, content type)."""
    s = get_settings()
    limit = s.max_upload_mb * 1024 * 1024
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise AppError(413, "payload_too_large", f"Images must be {s.max_upload_mb} MB or smaller")
    if not data:
        raise AppError(422, "validation_error", "The uploaded file is empty")
    ctype = sniff_image_type(data[:16])
    if ctype is None:
        raise AppError(415, "unsupported_media_type", "Only JPEG, PNG or WebP images are allowed")
    rel = Path("properties") / str(property_id) / f"{uuid.uuid4().hex}.{_EXT[ctype]}"
    dest = Path(s.storage_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return rel.as_posix(), ctype


def delete_file(rel_path: str) -> None:
    p = Path(get_settings().storage_dir) / rel_path
    if p.is_file():
        p.unlink()
