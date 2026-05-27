from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.schemas.detect import DetectRequest
from app.services.image_processor import (
    decode_base64_image,
    encode_image_base64,
    resize_image_bytes,
)
from app.services.upstream_client import UpstreamClient


class DetectService:
    def __init__(self, settings: Settings, upstream: UpstreamClient) -> None:
        self._settings = settings
        self._upstream = upstream

    async def process(self, request: DetectRequest) -> tuple[int, dict[str, Any]]:
        payload = await self._prepare_payload(request)
        return await self._upstream.detect(payload)

    async def _prepare_payload(self, request: DetectRequest) -> dict[str, Any]:
        payload = request.model_dump()
        image_settings = self._settings.image

        for item in payload.get("inputs", []):
            image_bytes: bytes | None = None

            if item.get("image_base64"):
                image_bytes, _ = decode_base64_image(item["image_base64"])
            elif item.get("image_url"):
                image_bytes = await self._upstream.fetch_image_url(item["image_url"])
            else:
                continue

            try:
                processed, _fmt, _resized = resize_image_bytes(
                    image_bytes, image_settings
                )
                item["image_base64"] = encode_image_base64(processed)
                # 8009 要求 image_url 字段存在，未使用时传空字符串
                if item.get("image_url") is None:
                    item["image_url"] = ""
            finally:
                del image_bytes

        return payload
