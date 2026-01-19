#!/usr/bin/env python3
"""
单元测试：DataFactoryPipeline.query_knowledge
- 不使用 Mock
- 若未配置豆包 API Key，则跳过
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.backend.factory import DataFactoryPipeline
from del_agent.storage.vector_store import create_vector_store


def main() -> int:
    api_key = os.getenv("ARK_API_KEY") or os.getenv("DOBAO_API_KEY")
    if not api_key:
        print("[SKIP] 未检测到 ARK_API_KEY/DOBAO_API_KEY，跳过测试")
        return 0

    llm = OpenAICompatibleProvider(
        model_name="doubao-seed-1-6-251015",
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=30
    )

    vector_store = create_vector_store({})
    pipeline = DataFactoryPipeline(
        llm_provider=llm,
        vector_store=vector_store,
        enable_verification=False,
        trace_backend=False
    )

    results = asyncio_run(pipeline.query_knowledge("张老师怎么样", user_id="test_user", limit=3))
    assert isinstance(results, list)
    print(f"[OK] query_knowledge 返回 {len(results)} 条")
    return 0


def asyncio_run(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.run(coro)
    return asyncio.run(coro)


if __name__ == "__main__":
    raise SystemExit(main())
