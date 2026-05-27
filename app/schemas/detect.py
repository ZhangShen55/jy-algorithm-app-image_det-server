from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    session_id: str = "string"


class DetectInput(BaseModel):
    image_base64: str | None = None
    image_url: str | None = None


class DetectFunctions(BaseModel):
    detection_type: str = "diagnosis"
    ret_result_file_base64_flag: bool = False


class DetectRequest(BaseModel):
    context: RequestContext
    inputs: list[DetectInput]
    functions: DetectFunctions


class ResponseContext(BaseModel):
    session_id: str | None = None
    status: str | None = None
    message: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class DetectResponse(BaseModel):
    context: ResponseContext | dict[str, Any] | None = None
    outputs: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}
