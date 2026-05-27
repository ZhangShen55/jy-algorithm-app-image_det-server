from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class UpstreamClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        timeout = httpx.Timeout(
            settings.upstream.timeout_seconds,
            connect=settings.upstream.connect_timeout_seconds,
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        limit = max(1, settings.upstream.max_concurrent_upstream)
        self._semaphore = asyncio.Semaphore(limit)

    @property
    def detect_url(self) -> str:
        return self._settings.upstream.detect_url

    @property
    def health_url(self) -> str:
        return self._settings.upstream.health_url

    async def check_health(self) -> bool:
        try:
            response = await self._client.get(self.health_url)
            return response.status_code < 500
        except httpx.HTTPError as exc:
            logger.warning("上游健康检查失败: %s", exc)
            return False

    async def detect(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        last_error: httpx.HTTPError | None = None
        for attempt in range(2):
            try:
                async with self._semaphore:
                    response = await self._client.post(self.detect_url, json=payload)
                try:
                    body = response.json()
                except ValueError:
                    body = {"detail": response.text}
                if response.status_code == 200 or attempt == 1:
                    return response.status_code, body
                if response.status_code >= 500:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                return response.status_code, body
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("上游请求异常 attempt=%s: %s", attempt + 1, exc)
                await asyncio.sleep(0.5 * (attempt + 1))
        assert last_error is not None
        raise last_error

    async def fetch_image_url(self, url: str) -> bytes:
        response = await self._client.get(url)
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        await self._client.aclose()
