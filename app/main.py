from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import load_settings
from app.core.lifespan import lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title="Image Detection Upstream Proxy",
    description="上游图像检测代理：超限图像等比缩放后转发至 8009 服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)


def main() -> None:
    """从 config.toml 读取 host/port 并启动 uvicorn。"""
    settings = load_settings(force=True)
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
