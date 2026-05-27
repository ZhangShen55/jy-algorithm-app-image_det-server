FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 容器内通过挂载 config.toml 到该路径
    CONFIG_PATH=/app/config/config.toml

WORKDIR /app

# 运行时依赖（curl 用于健康检查）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY app ./app

# 配置目录：运行时挂载 config.toml，镜像内不打包业务配置
RUN mkdir -p /app/config

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:8010/health" || exit 1

# 使用 app.main 启动，host/port 从挂载的 config.toml 读取
CMD ["python", "-m", "app.main"]
