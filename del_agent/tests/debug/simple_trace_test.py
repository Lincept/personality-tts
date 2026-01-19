#!/usr/bin/env python3
"""简单测试脚本：验证 trace 输出"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.resolve()))

from del_agent.frontend.orchestrator import FrontendOrchestrator
from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.utils.config import ConfigManager

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
    
    orchestrator = FrontendOrchestrator(
        llm_provider=llm_provider,
        trace_frontend=True,
        trace_print=print
    )
    
    print('='*60)
    print('Test: trace_frontend=True')
    print('='*60)
    
    result = await orchestrator.process_user_input(
        user_id='test_user',
        user_input='上交的王明老师一点都不爱学生'
    )
    
    print('-'*60)
    print(f'Result: intent={result.get("intent_type")}, success={result["success"]}')
    print(f'Response: {result.get("response_text", "")[:100]}...')

if __name__ == "__main__":
    asyncio.run(test())
