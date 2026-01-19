#!/usr/bin/env python3
"""
调试测试脚本：验证 trace 输出效果
测试前端和后端的详细过程输出
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from del_agent.frontend.orchestrator import FrontendOrchestrator
from del_agent.backend.factory import DataFactoryPipeline
from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.utils.config import ConfigManager
from del_agent.models.schemas import RawReview


def _truncate(text: str, max_len: int = 180) -> str:
    if text is None:
        return ""
    text = str(text).replace("\n", " ")
    return text if len(text) <= max_len else (text[: max_len - 3] + "...")


async def test_frontend_trace():
    """测试前端 trace 输出"""
    print("\n" + "=" * 70)
    print("测试1：前端 trace 输出（trace_frontend=True）")
    print("=" * 70)

    config_manager = ConfigManager("del_agent/config/settings.yaml")
    llm_config = config_manager.get_llm_config('doubao')
    if not llm_config.api_key:
        print("[SKIP] 未检测到 API Key，跳过测试")
        return

    llm_provider = OpenAICompatibleProvider(
        model_name=llm_config.model_name,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        timeout=llm_config.timeout
    )

    # 创建 orchestrator，启用 trace_frontend
    orchestrator = FrontendOrchestrator(
        llm_provider=llm_provider,
        trace_frontend=True,
        trace_print=print
    )

    # 测试用例
    test_cases = [
        ("chat", "你好，今天天气怎么样？"),
        ("provide_info", "上交的王明老师一点都不爱学生")
    ]

    for intent_label, user_input in test_cases:
        print("\n" + "-" * 60)
        print(f"[TEST] 预期意图: {intent_label}")
        print(f"[USER] {_truncate(user_input, 160)}")
        print("-" * 60)

        result = await orchestrator.process_user_input(
            user_id="test_user",
            user_input=user_input
        )

        print("-" * 60)
        print(f"[RESULT] success={result['success']}, intent={result.get('intent_type')}")
        print(f"[RESPONSE] {_truncate(result.get('response_text', ''), 200)}")


async def test_backend_trace():
    """测试后端 trace 输出"""
    print("\n" + "=" * 70)
    print("测试2：后端 trace 输出（trace_backend=True）")
    print("=" * 70)

    config_manager = ConfigManager("del_agent/config/settings.yaml")
    llm_config = config_manager.get_llm_config('doubao')
    if not llm_config.api_key:
        print("[SKIP] 未检测到 API Key，跳过测试")
        return

    llm_provider = OpenAICompatibleProvider(
        model_name=llm_config.model_name,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        timeout=llm_config.timeout
    )

    # 创建后端 pipeline，启用 trace_backend
    backend_pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=False,
        trace_backend=True,
        trace_print=print
    )

    # 测试评论
    raw_review = RawReview(
        content="这个导师就是学术妲己，整天画大饼，根本不管学生死活！",
        source_metadata={"school": "上海交通大学", "mentor_name": "张三"}
    )

    print("\n" + "-" * 60)
    print(f"[INPUT] {_truncate(raw_review.content, 200)}")
    print("-" * 60)

    result = await backend_pipeline.process_raw_review(raw_review)

    print("-" * 60)
    print(f"[OUTPUT] mentor_id={result.mentor_id}, dimension={result.dimension}")
    print(f"[OUTPUT] fact_content={_truncate(result.fact_content, 200)}")


async def test_full_trace():
    """测试完整流程 trace 输出（前端+后端）"""
    print("\n" + "=" * 70)
    print("测试3：完整流程 trace（trace_frontend=True, trace_backend=True）")
    print("=" * 70)

    config_manager = ConfigManager("del_agent/config/settings.yaml")
    llm_config = config_manager.get_llm_config('doubao')
    if not llm_config.api_key:
        print("[SKIP] 未检测到 API Key，跳过测试")
        return

    llm_provider = OpenAICompatibleProvider(
        model_name=llm_config.model_name,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        timeout=llm_config.timeout
    )

    # 创建后端 pipeline
    backend_pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=False,
        trace_backend=True,
        trace_print=print
    )

    # 创建前端 orchestrator
    orchestrator = FrontendOrchestrator(
        llm_provider=llm_provider,
        backend_pipeline=backend_pipeline,
        trace_frontend=True,
        trace_print=print
    )

    # 测试提供信息流程（会触发后端处理）
    user_input = "复旦的李四老师科研经费非常充足，每年都能发很多顶会论文"

    print("\n" + "-" * 60)
    print(f"[USER] {_truncate(user_input, 200)}")
    print("-" * 60)

    result = await orchestrator.process_user_input(
        user_id="test_user",
        user_input=user_input
    )

    print("-" * 60)
    print(f"[RESULT] success={result['success']}, intent={result.get('intent_type')}")
    print(f"[RESPONSE] {_truncate(result.get('response_text', ''), 200)}")


async def main():
    """运行所有测试"""
    print("=" * 70)
    print("DEL Agent - Trace 输出测试")
    print("=" * 70)

    await test_frontend_trace()
    await test_backend_trace()
    await test_full_trace()

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
