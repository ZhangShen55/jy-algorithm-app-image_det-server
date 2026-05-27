from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI

from app.core.config import Settings, load_settings
from app.services.upstream_client import UpstreamClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = load_settings(force=True)
    client = UpstreamClient(settings)
    app.state.settings = settings
    app.state.upstream_client = client

    alive = await client.check_health()
    if alive:
        logger.info("上游服务可用: %s", settings.upstream.health_url)
    else:
        logger.warning(
            "上游服务健康检查未通过: %s，服务仍将启动",
            settings.upstream.health_url,
        )

    try:
        yield
    finally:
        await client.close()
