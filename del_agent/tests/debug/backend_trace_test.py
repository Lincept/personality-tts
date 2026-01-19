#!/usr/bin/env python3
"""测试后端 trace 输出"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.resolve()))

from del_agent.backend.factory import DataFactoryPipeline
from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.utils.config import ConfigManager
from del_agent.models.schemas import RawReview

async def test():
    config_manager = ConfigManager('del_agent/config/settings.yaml')
    llm_config = config_manager.get_llm_config('doubao')
    if not llm_config.api_key:
        print('[SKIP] No API Key')
        return
    
    llm_provider = OpenAICompatibleProvider(
        model_name=llm_config.model_name,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        timeout=llm_config.timeout
    )
    
    backend_pipeline = DataFactoryPipeline(
        llm_provider=llm_provider,
        enable_verification=False,
        trace_backend=True,
        trace_print=print
    )
    
    print('='*60)
    print('Test: trace_backend=True')
    print('='*60)
    
    raw_review = RawReview(
        content="这个导师就是学术妲己，整天画大饼，根本不管学生死活！",
        source_metadata={"school": "上海交通大学", "mentor_name": "张三"}
    )
    
    print(f'[INPUT] {raw_review.content}')
    print('-'*60)
    
    result = await backend_pipeline.process_raw_review(raw_review)
    
    print('-'*60)
    print(f'[OUTPUT] mentor_id={result.mentor_id}, dimension={result.dimension}')
    print(f'[OUTPUT] fact_content={result.fact_content[:100]}...')

if __name__ == "__main__":
    asyncio.run(test())
