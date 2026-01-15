"""
真正的实时流式管道
LLM 流式输出 → 实时 TTS (逐字输入) → 流式播放 (边接收边播放)
"""
import threading
import queue
import time
from typing import Generator


class RealtimeStreamingPipeline:
    """实时流式处理管道"""

    def __init__(self):
        """初始化管道"""
        self.text_buffer = ""
        self.stop_event = threading.Event()

    def run(self, llm_stream: Generator[str, None, None],
            realtime_tts_client, streaming_player,
            display_text: bool = True):
        """
        运行实时流式管道

        Args:
            llm_stream: LLM 流式输出生成器
            realtime_tts_client: 实时 TTS 客户端 (Qwen3RealtimeTTS 或 VolcengineRealtimeTTS)
            streaming_player: StreamingAudioPlayer 播放器
            display_text: 是否显示文本
        """
        # 启动 TTS 会话 - 根据客户端类型使用不同参数
        client_type = type(realtime_tts_client).__name__

        if client_type == "Qwen3RealtimeTTS":
            # Qwen3 支持 mode 参数
            audio_queue = realtime_tts_client.start_session(
                mode="server_commit",  # 服务端自动断句
                audio_format="pcm",
                sample_rate=24000
            )
        elif client_type == "VolcengineRealtimeTTS":
            # 火山引擎不支持 mode 参数
            audio_queue = realtime_tts_client.start_session(
                audio_format="pcm",  # 使用 PCM 格式避免电流声
                sample_rate=24000
            )
        else:
            # 默认调用（不传参数）
            audio_queue = realtime_tts_client.start_session()

        # 启动播放器线程
        player_thread = threading.Thread(
            target=streaming_player.play_stream,
            args=(audio_queue, True),
            daemon=True
        )
        player_thread.start()

        print('🤖 学姐: ', end='', flush=True)

        # 从 LLM 读取文本并实时发送到 TTS
        full_text = []
        interrupted = False
        try:
            for chunk in llm_stream:
                # 检查是否被打断
                if self.stop_event.is_set():
                    interrupted = True
                    # 被打断后，继续静默读取 LLM 流（不播放），确保完整文本被收集用于记忆
                    # 但不显示文本，也不发送到 TTS
                    full_text.append(chunk)
                    continue

                # 显示文本
                if display_text:
                    print(chunk, end='', flush=True)

                full_text.append(chunk)

                # 实时发送到 TTS（Prompt 已经控制不输出格式符号）
                realtime_tts_client.send_text(chunk)

                # 小延迟，避免发送过快
                time.sleep(0.01)

        except Exception as e:
            print(f'\n❌ 错误: {e}')

        # 通知 TTS 结束
        realtime_tts_client.finish()

        # 等待 TTS 完成 - 根据客户端类型
        if hasattr(realtime_tts_client, 'wait_for_completion'):
            realtime_tts_client.wait_for_completion(timeout=30)

        # 等待播放完成
        player_thread.join(timeout=10)

        # 获取性能指标（静默模式）
        metrics = realtime_tts_client.get_metrics()

        # 注意：不再自动断开连接，复用全局 TTS 客户端

        print()

        return {
            "text": "".join(full_text),
            "metrics": metrics
        }

    def stop(self):
        """停止管道"""
        self.stop_event.set()
