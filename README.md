# Image Detection Upstream Proxy

上游图像检测代理服务（端口 **8010**），接口与 `8009` 下游一致。对超过 `1920×1080` 边界的图像在内存中等比缩放后再转发，避免下游崩溃。

## 接口

- `POST /PerceptionService/Detect` — 与下游请求/响应体一致
- `GET /health` — 本服务及上游存活探测

## 配置

编辑项目根目录 `config.toml`（**修改后必须重启服务**才会生效）：

也可通过环境变量指定配置文件路径：

```bash
export CONFIG_PATH=/path/to/config.toml
python -m app.main
```

启动后访问 `GET /health` 可查看当前**实际生效**的配置（`config` 字段）。

```toml
[upstream]
host = "10.80.5.130"
port = 8009
detect_path = "/PerceptionService/Detect"
timeout_seconds = 60.0
```

## 环境

```bash
conda env create -f environment.yml
conda activate image_det
```

## 启动

进入项目根目录并激活环境：

```bash
cd /path/to/jy-algorithm-app-image_det-server
conda activate image_det
```

启动时会自动 GET `http://<upstream.host>:<upstream.port>/` 检查上游是否存活。

### 方式一：`python -m app.main`（推荐）

从 `config.toml` 的 `[server]` 读取 `host`、`port`，无需手写启动参数。

**前台运行：**

```bash
python -m app.main
```

**后台运行：**

```bash
nohup python -m app.main > /tmp/8010.log 2>&1 &
tail -f /tmp/8010.log
```

**指定配置文件：**

```bash
CONFIG_PATH=/path/to/config.toml python -m app.main
```

**停止服务：**

```bash
kill $(lsof -t -i:8010)
```

### 方式二：`uvicorn` 命令行

适合部署脚本、容器或需要显式指定进程参数的场景。  
注意：`--host` / `--port` 以命令行为准，**不会**读取 `config.toml` 的 `[server]`；业务配置（upstream、image 等）仍从 `config.toml` 加载。

**基础启动（单进程）：**

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8010 \
  --loop asyncio \
  --http httptools \
  --no-access-log
```

**常用完整参数示例：**

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8010 \
  --workers 1 \
  --loop asyncio \
  --http httptools \
  --timeout-keep-alive 75 \
  --limit-concurrency 200 \
  --backlog 2048 \
  --log-level info \
  --no-access-log
```

**开发热重载（仅开发环境）：**

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8010 \
  --reload \
  --reload-dir app
```

**后台运行：**

```bash
nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8010 \
  --loop asyncio \
  --http httptools \
  > /tmp/8010.log 2>&1 &
```

**指定配置文件（upstream 等仍从 toml 读取）：**

```bash
CONFIG_PATH=/path/to/config.toml uvicorn app.main:app --host 0.0.0.0 --port 8010
```

### 方式三：`run.py`（兼容入口）

等价于 `python -m app.main`：

```bash
python run.py
```

### 启动方式对比

| 启动方式 | host/port 来源 | 适用场景 |
|---------|----------------|----------|
| `python -m app.main` | `config.toml` `[server]` | 日常开发、生产（推荐） |
| `uvicorn app.main:app --host ... --port ...` | 命令行参数 | K8s/脚本/需固定 CLI 参数 |
| `python run.py` | 同 `app.main` | 兼容旧习惯 |

### 验证服务

```bash
curl http://127.0.0.1:8010/health
```

## 测试

```bash
conda activate image_det
pytest tests/test_image_processor.py tests/test_detect_api.py -v
```

## 压测（8 / 16 / 24 / 64 并发）

先启动服务，再执行：

```bash
conda activate image_det
python scripts/run_stress.py
# 或
pytest tests/stress/test_stress.py -v -m stress
```

压测与线上处理均**不落盘**，图像仅在内存中编解码。

## 缩放规则

- 宽度 &gt; 1920 或高度 &gt; 1080 时触发等比缩放
- 缩放后：宽度 ≤ 1920 且高度 ≤ 1080（边界值 1920×1080 不缩放）
