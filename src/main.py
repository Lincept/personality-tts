"""
主测试脚本 - LLM + TTS 集成测试
支持实时流式对话和实时语音播放
"""
import os
import sys
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm.llm_client import LLMClient
from src.tts.qwen3_realtime_tts import Qwen3RealtimeTTS
from src.tts.volcengine_realtime_tts import VolcengineRealtimeTTS
from src.audio.pyaudio_player import PyAudioStreamPlayer
from src.config_loader import ConfigLoader
from src.realtime_pipeline import RealtimeStreamingPipeline
from src.voice_assistant_prompt import VoiceAssistantPrompt
from src.role_loader import RoleLoader
from src.memory.mem0_manager import Mem0Manager


class LLMTTSTest:
    def __init__(self, config_path: str = "config/api_keys.json", role_config: dict = None):
        """
        初始化测试类

        Args:
            config_path: 配置文件路径
            role_config: 角色配置（从 role_loader 加载）
        """
        # 使用新的配置加载器
        config_loader = ConfigLoader()
        self.config = config_loader.get_config()

        # 静默打印配置状态
        # config_loader.print_status()

        self.test_config = self._load_test_config()
        self.llm_client = None
        self.output_dir = self.test_config.get("output_dir", "data/audios")

        # 初始化 Mem0 记忆管理器
        mem0_config = self.config.get("mem0", {})
        self.mem0_manager = None
        if mem0_config.get("enable_mem0", False):
            self.mem0_manager = Mem0Manager(mem0_config)

        # 用户ID（从配置获取）
        self.user_id = mem0_config.get("user_id", "default_user")

        # 初始化语音助手 Prompt 管理器（传入角色配置和 Mem0 管理器）
        self.voice_prompt = VoiceAssistantPrompt(role_config=role_config, mem0_manager=self.mem0_manager)

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_test_config(self) -> dict:
        """加载测试配置"""
        with open("config/test_config.json", 'r', encoding='utf-8') as f:
            return json.load(f)

    def initialize_llm(self):
        """初始化LLM客户端"""
        llm_config = self.config.get("openai_compatible", {})
        self.llm_client = LLMClient(
            api_key=llm_config.get("api_key"),
            base_url=llm_config.get("base_url"),
            model=llm_config.get("model")
        )
        # print(f"✓ LLM客户端初始化完成: {self.llm_client.get_model_info()}")  # 静默初始化

    def chat_and_speak_realtime(self, prompt: str, play_audio: bool = True):
        """
        真正的实时对话（Qwen3 版本）
        LLM 流式输出 → 实时 TTS (逐字输入) → 流式播放 (边接收边播放)

        Args:
            prompt: 用户输入
            play_audio: 是否播放音频
        """
        print(f"\n{'='*60}")
        print(f"用户: {prompt}")
        print(f"{'='*60}")

        # 初始化 LLM
        if not self.llm_client:
            self.initialize_llm()

        # 使用语音助手 Prompt 构建消息（传入 user_id）
        messages = self.voice_prompt.get_messages(prompt, user_id=self.user_id)

        # 创建实时 TTS 客户端
        config = self.config.get("qwen3_tts", {})
        realtime_tts = Qwen3RealtimeTTS(
            api_key=config.get("api_key"),
            voice="Cherry"
        )

        # 创建流式播放器 - PyAudio
        streaming_player = PyAudioStreamPlayer(sample_rate=24000)
        print('[系统] 使用 PyAudio 播放器')

        # 创建实时管道
        pipeline = RealtimeStreamingPipeline()

        # 获取 LLM 流式输出（使用完整的消息列表）
        llm_stream = self.llm_client.chat_stream(
            messages=messages,
            temperature=self.test_config["llm_config"]["temperature"]
        )

        # 运行实时管道
        result = pipeline.run(
            llm_stream=llm_stream,
            realtime_tts_client=realtime_tts,
            streaming_player=streaming_player,
            display_text=True
        )

        # 保存对话历史（短期）
        self.voice_prompt.add_conversation('user', prompt)
        self.voice_prompt.add_conversation('assistant', result["text"])

        # 保存到 Mem0（长期记忆）
        if self.mem0_manager:
            self.mem0_manager.add_conversation(
                user_input=prompt,
                assistant_response=result["text"],
                user_id=self.user_id
            )

        print("\n✓ 实时流式处理完成")

        return {
            "prompt": prompt,
            "response": result["text"],
            "mode": "realtime",
            "metrics": result["metrics"]
        }

    def chat_and_speak_realtime_volcengine(self, prompt: str, play_audio: bool = True):
        """
        火山引擎实时对话
        LLM 流式输出 → 实时 TTS (逐字输入) → 流式播放 (边接收边播放)

        Args:
            prompt: 用户输入
            play_audio: 是否播放音频
        """
        print(f"\n{'='*60}")
        print(f"用户: {prompt}")
        print(f"{'='*60}")

        # 初始化 LLM
        if not self.llm_client:
            self.initialize_llm()

        # 使用语音助手 Prompt 构建消息（传入 user_id）
        messages = self.voice_prompt.get_messages(prompt, user_id=self.user_id)

        # 创建实时 TTS 客户端
        config = self.config.get("volcengine_seed2", {})
        realtime_tts = VolcengineRealtimeTTS(
            app_id=config.get("app_id"),
            access_token=config.get("access_token") or config.get("api_key"),
            voice="zh_female_cancan_mars_bigtts"
        )

        # 创建流式播放器 - PyAudio
        streaming_player = PyAudioStreamPlayer(sample_rate=24000)
        print('[系统] 使用 PyAudio 播放器')

        # 创建实时管道
        pipeline = RealtimeStreamingPipeline()

        # 获取 LLM 流式输出（使用完整的消息列表）
        llm_stream = self.llm_client.chat_stream(
            messages=messages,
            temperature=self.test_config["llm_config"]["temperature"]
        )

        # 运行实时管道
        result = pipeline.run(
            llm_stream=llm_stream,
            realtime_tts_client=realtime_tts,
            streaming_player=streaming_player,
            display_text=True
        )

        # 注意：disconnect() 已在 pipeline.run() 中调用

        # 保存对话历史（短期）
        self.voice_prompt.add_conversation('user', prompt)
        self.voice_prompt.add_conversation('assistant', result["text"])

        # 保存到 Mem0（长期记忆）
        if self.mem0_manager:
            self.mem0_manager.add_conversation(
                user_input=prompt,
                assistant_response=result["text"],
                user_id=self.user_id
            )

        print("\n✓ 实时流式处理完成")

        return {
            "prompt": prompt,
            "response": result["text"],
            "mode": "realtime_volcengine",
            "metrics": result["metrics"]
        }

    def interactive_mode(self, use_realtime: bool = True):
        """
        交互式对话模式

        Args:
            use_realtime: 是否使用实时模式（默认开启）
        """
        print("\n" + "="*60)
        print("🎙️  语音助手交互模式")
        print("="*60)
        print("\n命令:")
        print("  /quit - 退出")
        print("  /provider - 切换 TTS 提供商 (qwen3/volcengine)")
        print("  /role <角色> - 切换角色 (default/casual/professional/companion)")
        print("  /clear - 清空对话历史")
        print("  /history - 查看对话历史")
        print("  /setname <名字> - 设置用户名")
        print("  /addknowledge <内容> - 添加知识库")
        print("  /memories - 查看长期记忆 (Mem0)")
        print("  /clearmem - 清除长期记忆 (Mem0)")
        print("  /user <用户ID> - 切换用户 (Mem0)")
        print("  /info - 查看当前配置")
        print()

        current_provider = "qwen3"

        provider_desc = {
            "qwen3": "通义千问 实时 TTS",
            "volcengine": "火山引擎 实时 TTS"
        }

        print(f"当前 TTS: {provider_desc[current_provider]}\n")

        while True:
            try:
                user_input = input("你: ").strip()

                if not user_input:
                    continue

                if user_input == "/quit":
                    print("再见!")
                    break

                elif user_input == "/provider":
                    # 循环切换 TTS 提供商
                    providers = ["qwen3", "volcengine"]
                    current_idx = providers.index(current_provider)
                    current_provider = providers[(current_idx + 1) % len(providers)]
                    print(f"✓ 已切换到: {provider_desc[current_provider]}")

                elif user_input == "/clear":
                    self.voice_prompt.clear_history()
                    print("✓ 对话历史已清空")

                elif user_input.startswith("/role"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        role = parts[1]
                        try:
                            self.voice_prompt.set_role(role)
                            role_info = self.voice_prompt.get_role_info()
                            print(f"✓ 已切换到角色: {role_info['name']}")
                            print(f"  风格: {role_info['style']}")
                            print(f"  特点: {role_info['personality']}")
                        except ValueError as e:
                            print(f"❌ {str(e)}")
                    else:
                        current_role = self.voice_prompt.get_role_info()
                        print(f"当前角色: {current_role['name']}")
                        print("可选角色: default, casual, professional, companion")

                elif user_input == "/history":
                    summary = self.voice_prompt.get_conversation_summary()
                    print(f"\n对话历史:\n{summary}\n")

                elif user_input.startswith("/setname"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        name = parts[1]
                        self.voice_prompt.set_user_info(name=name)
                        print(f"✓ 用户名已设置为: {name}")
                    else:
                        print("❌ 请提供用户名，例如: /setname 小明")

                elif user_input.startswith("/addknowledge"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        knowledge = parts[1]
                        self.voice_prompt.add_knowledge(knowledge)
                        print(f"✓ 已添加知识: {knowledge}")
                    else:
                        print("❌ 请提供知识内容，例如: /addknowledge 用户喜欢攀岩")

                elif user_input == "/memories":
                    # 查看长期记忆
                    if self.mem0_manager:
                        memories = self.mem0_manager.get_all_memories(self.user_id)
                        if memories:
                            print(f"\n长期记忆 (用户: {self.user_id}):")
                            for i, mem in enumerate(memories, 1):
                                print(f"{i}. {mem['memory']}")
                            print()
                        else:
                            print("暂无长期记忆")
                    else:
                        print("Mem0 未启用")

                elif user_input == "/clearmem":
                    # 清除长期记忆
                    if self.mem0_manager:
                        self.mem0_manager.clear_memories(self.user_id)
                    else:
                        print("Mem0 未启用")

                elif user_input.startswith("/user"):
                    # 切换用户
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        self.user_id = parts[1]
                        print(f"✓ 已切换到用户: {self.user_id}")
                    else:
                        print(f"当前用户: {self.user_id}")

                elif user_input == "/info":
                    role_info = self.voice_prompt.get_role_info()
                    print("\n当前配置:")
                    print(f"  TTS 提供商: {provider_desc[current_provider]}")
                    print(f"  角色: {role_info['name']} ({role_info['personality']})")
                    print(f"  对话轮数: {len(self.voice_prompt.conversation_history) // 2}")
                    print(f"  知识库条目: {len(self.voice_prompt.knowledge_base)}")
                    if self.mem0_manager:
                        mem_count = len(self.mem0_manager.get_all_memories(self.user_id))
                        print(f"  长期记忆: {mem_count} 条 (用户: {self.user_id})")
                    print()

                else:
                    # 实时对话
                    if current_provider == "qwen3":
                        self.chat_and_speak_realtime(user_input)
                    elif current_provider == "volcengine":
                        self.chat_and_speak_realtime_volcengine(user_input)

            except KeyboardInterrupt:
                print("\n\n再见!")
                break
            except Exception as e:
                print(f"\n❌ 错误: {str(e)}\n")
                import traceback
                traceback.print_exc()


def main():
    """主函数"""
    # 加载角色
    print("\n正在加载角色...")
    role_loader = RoleLoader()

    # 让用户选择角色
    selected_role_id = role_loader.select_role_interactive()

    # 获取角色配置
    role_config = None
    if selected_role_id:
        role_config = role_loader.get_role(selected_role_id)
        print(f"\n✓ 使用角色: {role_config['name']}")
        print(f"  特点: {role_config['personality']}")
        print(f"  风格: {role_config['style']}\n")

    # 初始化测试类（传入角色配置）
    test = LLMTTSTest(role_config=role_config)

    # 默认进入交互模式
    test.interactive_mode()


if __name__ == "__main__":
    main()
