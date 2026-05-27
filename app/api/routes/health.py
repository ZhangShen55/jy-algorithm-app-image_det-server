from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.config import settings_as_dict

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    upstream = request.app.state.upstream_client
    upstream_ok = await upstream.check_health()
    return {
        "status": "ok",
        "upstream_alive": upstream_ok,
        "upstream_url": upstream.health_url,
        "config": settings_as_dict(),
    }
