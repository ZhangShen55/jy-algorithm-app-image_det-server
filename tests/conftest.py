from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from app.core.config import get_settings, reset_settings
from app.main import app
from app.services.upstream_client import UpstreamClient

TEST_DIR = Path(__file__).resolve().parent / "test"


@pytest.fixture(autouse=True)
def _reset_config_cache():
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
async def app_lifespan():
    from app.core.config import load_settings

    settings = load_settings(force=True)
    upstream = UpstreamClient(settings)
    app.state.settings = settings
    app.state.upstream_client = upstream
    yield
    await upstream.close()


@pytest.fixture
async def client(app_lifespan):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def load_image_b64(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


@pytest.fixture
def image_4k_png_b64() -> str:
    return load_image_b64(TEST_DIR / "4k-1.png")


@pytest.fixture
def image_4k_jpg_b64() -> str:
    return load_image_b64(TEST_DIR / "4k-2.jpg")


@pytest.fixture
def image_1080p_b64() -> str:
    return load_image_b64(TEST_DIR / "非4k.jpeg")


def make_synthetic_b64(width: int, height: int, fmt: str = "JPEG") -> str:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.fixture
def image_2560x1440_b64() -> str:
    return make_synthetic_b64(2560, 1440)


@pytest.fixture
def image_2000x500_b64() -> str:
    return make_synthetic_b64(2000, 500)


@pytest.fixture
def image_800x2000_b64() -> str:
    return make_synthetic_b64(800, 2000)


@pytest.fixture
def image_1918x1078_b64() -> str:
    return make_synthetic_b64(1918, 1078)
