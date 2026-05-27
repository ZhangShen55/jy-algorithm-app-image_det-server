#!/usr/bin/env python3
"""独立压测脚本：8/16/24/64 并发，多尺寸，需先启动 python run.py"""

from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tests.stress.test_stress import (  # noqa: E402
    CONCURRENCY_LEVELS,
    STRESS_CASES,
    _run_concurrency,
    _server_reachable,
)

STRESS_BASE_URL = os.getenv("STRESS_BASE_URL", "http://127.0.0.1:8010")


async def main() -> None:
    if not _server_reachable():
        print(f"服务未就绪: {STRESS_BASE_URL}/health")
        sys.exit(1)

    print(f"压测目标: {STRESS_BASE_URL}")
    failed = False
    for case_name, b64 in STRESS_CASES:
        for level in CONCURRENCY_LEVELS:
            result = await _run_concurrency(level, b64, case_name)
            ok = result["success"] == result["total"]
            failed = failed or not ok
            print(
                f"  [{case_name:12}] c={level:2d} "
                f"ok={result['success']}/{result['total']} "
                f"p50={result['p50_ms']:.0f}ms "
                f"p95={result['p95_ms']:.0f}ms "
                f"max={result['max_ms']:.0f}ms"
            )
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
