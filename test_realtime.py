"""
快速测试实时流式播放
"""
from src.main import LLMTTSTest

test = LLMTTSTest()

print("测试实时流式对话...")
test.chat_and_speak_realtime("你好，请简单介绍一下你自己")
