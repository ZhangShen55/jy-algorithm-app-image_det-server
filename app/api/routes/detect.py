from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.detect import DetectRequest
from app.services.detect_service import DetectService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["detect"])


@router.post("/PerceptionService/Detect")
async def detect(request: Request, body: DetectRequest) -> JSONResponse:
    settings = request.app.state.settings
    upstream = request.app.state.upstream_client
    service = DetectService(settings, upstream)

    try:
        status_code, response_body = await service.process(body)
    except httpx.HTTPError as exc:
        logger.exception("上游请求失败")
        return JSONResponse(
            status_code=502,
            content={
                "context": {
                    "status": "502",
                    "message": f"upstream unavailable: {exc}",
                }
            },
        )

    return JSONResponse(status_code=status_code, content=response_body)
