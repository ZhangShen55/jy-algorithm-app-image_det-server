from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_settings: "Settings | None" = None
_settings_path: Path | None = None


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8010


class UpstreamSettings(BaseModel):
    host: str = "10.80.5.130"
    port: int = 8009
    detect_path: str = "/PerceptionService/Detect"
    health_path: str = "/"
    timeout_seconds: float = 60.0
    connect_timeout_seconds: float = 10.0
    max_concurrent_upstream: int = 16

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def detect_url(self) -> str:
        return f"{self.base_url}{self.detect_path}"

    @property
    def health_url(self) -> str:
        return f"{self.base_url}{self.health_path}"


class ImageSettings(BaseModel):
    max_width: int = 1920
    max_height: int = 1080
    jpeg_quality: int = 90


class Settings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    upstream: UpstreamSettings = Field(default_factory=UpstreamSettings)
    image: ImageSettings = Field(default_factory=ImageSettings)


def resolve_config_path(config_path: str | Path | None = None) -> Path:
    """解析配置文件路径：优先 CONFIG_PATH 环境变量，其次参数，最后项目根目录。"""
    if config_path is not None:
        return Path(config_path).resolve()
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return Path(env_path).resolve()
    root = Path(__file__).resolve().parents[2]
    return (root / "config.toml").resolve()


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def load_settings(config_path: str | Path | None = None, *, force: bool = False) -> Settings:
    """从 config.toml 加载配置；force=True 时强制重新读取文件。"""
    global _settings, _settings_path

    path = resolve_config_path(config_path)
    if not force and _settings is not None and _settings_path == path:
        return _settings

    data = _load_toml(path)
    _settings = Settings.model_validate(data)
    _settings_path = path

    logger.info("已加载配置: %s", path)
    logger.info(
        "upstream=%s:%s timeout=%ss max_concurrent=%s image=%sx%s",
        _settings.upstream.host,
        _settings.upstream.port,
        _settings.upstream.timeout_seconds,
        _settings.upstream.max_concurrent_upstream,
        _settings.image.max_width,
        _settings.image.max_height,
    )
    return _settings


def get_settings(config_path: str | Path | None = None) -> Settings:
    """获取当前配置（首次调用时从磁盘加载）。"""
    if _settings is None:
        return load_settings(config_path)
    return _settings


def reset_settings() -> None:
    """清空内存缓存，下次 get_settings 会重新读文件。测试或热更新时使用。"""
    global _settings, _settings_path
    _settings = None
    _settings_path = None


def settings_as_dict() -> dict[str, Any]:
    """返回当前生效配置（用于 /health 展示）。"""
    s = get_settings()
    return {
        "config_path": str(_settings_path) if _settings_path else None,
        "server": s.server.model_dump(),
        "upstream": {
            **s.upstream.model_dump(),
            "detect_url": s.upstream.detect_url,
            "health_url": s.upstream.health_url,
        },
        "image": s.image.model_dump(),
    }
