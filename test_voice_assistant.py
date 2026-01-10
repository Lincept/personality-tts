"""
测试语音助手 Prompt 系统
"""
from src.main import LLMTTSTest

test = LLMTTSTest()

# 设置用户信息
test.voice_prompt.set_user_info(
    name="小明",
    preferences={"hobby": "攀岩"},
    context={"location": "北京"}
)

# 添加知识库
test.voice_prompt.add_knowledge("用户喜欢户外运动", category="兴趣")
test.voice_prompt.add_knowledge("用户是程序员", category="职业")

print("测试语音助手...")
print("\n第一轮对话:")
test.chat_and_speak_realtime("你好")

print("\n\n第二轮对话:")
test.chat_and_speak_realtime("推荐一个周末活动")
