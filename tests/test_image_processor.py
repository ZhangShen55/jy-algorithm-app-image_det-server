from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.core.config import ImageSettings
from app.services.image_processor import (
    compute_scale,
    decode_base64_image,
    get_image_size,
    needs_resize,
    resize_image_bytes,
    strip_data_uri_prefix,
)

TEST_DIR = Path(__file__).resolve().parent / "test"


@pytest.fixture
def image_settings() -> ImageSettings:
    return ImageSettings(max_width=1920, max_height=1080, jpeg_quality=90)


def test_strip_data_uri_prefix():
    raw = base64.b64encode(b"abc").decode()
    assert strip_data_uri_prefix(f"data:image/png;base64,{raw}") == raw


def test_needs_resize_4k(image_settings: ImageSettings):
    assert needs_resize(3840, 2160, image_settings) is True


def test_needs_resize_1080p(image_settings: ImageSettings):
    assert needs_resize(1920, 1080, image_settings) is False


def test_needs_resize_within(image_settings: ImageSettings):
    assert needs_resize(1918, 1078, image_settings) is False


@pytest.mark.parametrize(
    "width,height,expect_resize",
    [
        (3840, 2160, True),
        (2560, 1440, True),
        (2000, 500, True),
        (800, 2000, True),
        (1920, 1080, False),
        (1918, 1078, False),
        (1280, 720, False),
    ],
)
def test_resize_matrix(
    image_settings: ImageSettings, width: int, height: int, expect_resize: bool
):
    assert needs_resize(width, height, image_settings) is expect_resize


def test_resize_4k_output_within_limits(image_settings: ImageSettings):
    data = (TEST_DIR / "4k-1.png").read_bytes()
    out, _fmt, resized = resize_image_bytes(data, image_settings)
    assert resized is True
    w, h = get_image_size(out)
    assert w <= 1920
    assert h <= 1080


def test_resize_1080p_unchanged(image_settings: ImageSettings):
    data = (TEST_DIR / "非4k.jpeg").read_bytes()
    out, _fmt, resized = resize_image_bytes(data, image_settings)
    assert resized is False
    assert out == data


def test_compute_scale_4k(image_settings: ImageSettings):
    scale = compute_scale(3840, 2160, image_settings)
    w = int(3840 * scale)
    h = int(2160 * scale)
    assert w <= 1920
    assert h <= 1080


def test_decode_with_data_uri(image_settings: ImageSettings):
    data = (TEST_DIR / "4k-2.jpg").read_bytes()
    b64 = "data:image/jpeg;base64," + base64.b64encode(data).decode()
    raw, fmt = decode_base64_image(b64)
    assert fmt == "jpeg"
    assert raw == data
