from __future__ import annotations

import base64
import re
from io import BytesIO

from PIL import Image

from app.core.config import ImageSettings

_DATA_URI_PREFIX = re.compile(r"^data:image/[\w+.-]+;base64,", re.IGNORECASE)


def strip_data_uri_prefix(b64: str) -> str:
    return _DATA_URI_PREFIX.sub("", b64.strip())


def decode_base64_image(b64: str) -> tuple[bytes, str]:
    """解码 base64，返回原始字节与格式名（png/jpeg 等）。"""
    cleaned = strip_data_uri_prefix(b64)
    raw = base64.b64decode(cleaned, validate=False)
    fmt = _guess_format_from_bytes(raw)
    return raw, fmt


def _guess_format_from_bytes(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and len(data) > 12 and data[8:12] == b"WEBP":
        return "webp"
    return "jpeg"


def get_image_size(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as img:
        return img.size


def needs_resize(width: int, height: int, settings: ImageSettings) -> bool:
    """任一边超过 1920 或 1080 时需要缩放。"""
    return width > settings.max_width or height > settings.max_height


def compute_scale(width: int, height: int, settings: ImageSettings) -> float:
    if not needs_resize(width, height, settings):
        return 1.0
    return min(settings.max_width / width, settings.max_height / height)


def resize_image_bytes(data: bytes, settings: ImageSettings) -> tuple[bytes, str, bool]:
    """
    在内存中按需缩放图像，不落盘。
    返回 (新字节, 格式, 是否发生缩放)。
    """
    with Image.open(BytesIO(data)) as img:
        width, height = img.size
        if not needs_resize(width, height, settings):
            fmt = (img.format or _guess_format_from_bytes(data)).lower()
            if fmt == "jpg":
                fmt = "jpeg"
            return data, fmt, False

        scale = compute_scale(width, height, settings)
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))

        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        if resized.mode in ("RGBA", "LA", "P"):
            resized = resized.convert("RGB")
            out_fmt = "jpeg"
        else:
            src_fmt = (img.format or "JPEG").upper()
            out_fmt = "jpeg" if src_fmt in ("JPEG", "JPG") else "png"

        buf = BytesIO()
        if out_fmt == "jpeg":
            resized.save(buf, format="JPEG", quality=settings.jpeg_quality, optimize=True)
        else:
            resized.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), out_fmt, True


def encode_image_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
