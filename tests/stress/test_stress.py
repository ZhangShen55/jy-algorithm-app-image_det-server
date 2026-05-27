"""
压测：并发 8 / 16 / 24 / 64，多尺寸图像，全程内存处理不落盘。

运行前需启动服务: python run.py
可选环境变量 STRESS_BASE_URL=http://127.0.0.1:8010
"""

from __future__ import annotations

import asyncio
import base64
import os
import statistics
import time
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from PIL import Image

TEST_DIR = Path(__file__).resolve().parents[1] / "test"
STRESS_BASE_URL = os.getenv("STRESS_BASE_URL", "http://127.0.0.1:8010")
CONCURRENCY_LEVELS = [8, 16, 24, 64]


def _load_b64_in_memory(filename: str) -> str:
    data = (TEST_DIR / filename).read_bytes()
    return base64.b64encode(data).decode("ascii")


def _synthetic_b64(width: int, height: int) -> str:
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


STRESS_CASES = [
    ("4k-png", _load_b64_in_memory("4k-1.png")),
    ("4k-jpg", _load_b64_in_memory("4k-2.jpg")),
    ("1080p", _load_b64_in_memory("非4k.jpeg")),
    ("2560x1440", _synthetic_b64(2560, 1440)),
    ("2000x500", _synthetic_b64(2000, 500)),
    ("800x2000", _synthetic_b64(800, 2000)),
]


def _build_payload(b64: str, session_id: str) -> dict:
    return {
        "context": {"session_id": session_id},
        "inputs": [{"image_base64": b64}],
        "functions": {
            "detection_type": "diagnosis",
            "ret_result_file_base64_flag": False,
        },
    }


async def _single_request(
    client: httpx.AsyncClient, b64: str, session_id: str
) -> tuple[float, int]:
    start = time.perf_counter()
    response = await client.post(
        f"{STRESS_BASE_URL}/PerceptionService/Detect",
        json=_build_payload(b64, session_id),
    )
    elapsed = time.perf_counter() - start
    return elapsed, response.status_code


async def _run_concurrency(
    concurrency: int, b64: str, case_name: str, total_requests: int | None = None
) -> dict:
    total = total_requests or concurrency
    timeout = httpx.Timeout(300.0, connect=10.0)
    latencies: list[float] = []
    status_codes: list[int] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        sem = asyncio.Semaphore(concurrency)

        async def worker(idx: int) -> None:
            async with sem:
                elapsed, code = await _single_request(
                    client, b64, f"stress-{case_name}-{concurrency}-{idx}"
                )
                latencies.append(elapsed)
                status_codes.append(code)

        await asyncio.gather(*[worker(i) for i in range(total)])

    return {
        "concurrency": concurrency,
        "case": case_name,
        "total": total,
        "success": sum(1 for c in status_codes if c == 200),
        "p50_ms": statistics.median(latencies) * 1000,
        "p95_ms": sorted(latencies)[int(len(latencies) * 0.95) - 1] * 1000,
        "max_ms": max(latencies) * 1000,
    }


def _server_reachable() -> bool:
    try:
        with httpx.Client(timeout=3.0) as client:
            r = client.get(f"{STRESS_BASE_URL}/health")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="module")
def require_running_server():
    if not _server_reachable():
        pytest.skip(
            f"压测需要已启动的服务 {STRESS_BASE_URL}，请先运行: python run.py"
        )


@pytest.mark.stress
@pytest.mark.parametrize("concurrency", CONCURRENCY_LEVELS)
@pytest.mark.parametrize("case_name,b64", STRESS_CASES)
@pytest.mark.asyncio
async def test_stress_detect(
    require_running_server, concurrency: int, case_name: str, b64: str
):
    result = await _run_concurrency(concurrency, b64, case_name)
    print(
        f"\n[压测] case={result['case']} concurrency={result['concurrency']} "
        f"success={result['success']}/{result['total']} "
        f"p50={result['p50_ms']:.1f}ms p95={result['p95_ms']:.1f}ms "
        f"max={result['max_ms']:.1f}ms"
    )
    assert result["success"] == result["total"], (
        f"并发 {concurrency} 案例 {case_name} 存在非 200 响应"
    )
