from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

MOCK_SUCCESS = {
    "context": {
        "session_id": "test-session",
        "status": "200",
        "message": "success",
    },
    "outputs": [{"objects": []}],
}


@pytest.mark.asyncio
async def test_detect_returns_upstream_body(app_lifespan, image_4k_png_b64: str):
    with patch(
        "app.services.detect_service.UpstreamClient.detect",
        new_callable=AsyncMock,
        return_value=(200, MOCK_SUCCESS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "context": {"session_id": "test-session"},
                "inputs": [{"image_base64": image_4k_png_b64}],
                "functions": {
                    "detection_type": "diagnosis",
                    "ret_result_file_base64_flag": False,
                },
            }
            response = await client.post("/PerceptionService/Detect", json=payload)

    assert response.status_code == 200
    assert response.json()["context"]["status"] == "200"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_name",
    [
        "image_4k_png_b64",
        "image_4k_jpg_b64",
        "image_1080p_b64",
        "image_2560x1440_b64",
        "image_2000x500_b64",
        "image_800x2000_b64",
        "image_1918x1078_b64",
    ],
)
async def test_detect_multiple_sizes(app_lifespan, request, fixture_name: str):
    b64 = request.getfixturevalue(fixture_name)
    captured: dict = {}

    async def fake_detect(_self, payload):
        captured["payload"] = payload
        return 200, MOCK_SUCCESS

    with patch(
        "app.services.detect_service.UpstreamClient.detect",
        new=fake_detect,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/PerceptionService/Detect",
                json={
                    "context": {"session_id": "multi-size"},
                    "inputs": [{"image_base64": b64}],
                    "functions": {"detection_type": "diagnosis"},
                },
            )

    assert response.status_code == 200
    from app.core.config import get_settings
    from app.services.image_processor import decode_base64_image, get_image_size

    settings = get_settings()
    raw, _ = decode_base64_image(captured["payload"]["inputs"][0]["image_base64"])
    w, h = get_image_size(raw)
    assert w <= settings.image.max_width
    assert h <= settings.image.max_height
    assert captured["payload"]["inputs"][0].get("image_url") == ""


@pytest.mark.asyncio
async def test_health_endpoint(app_lifespan):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "app.services.upstream_client.UpstreamClient.check_health",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
