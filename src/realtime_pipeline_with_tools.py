"""
支持工具调用的实时流式管道
LLM 流式输出（含工具调用）→ 实时 TTS → 流式播放
"""
import threading
import queue
import time
from typing import Generator, Optional, Callable, List, Dict, Any
import json


class RealtimeStreamingPipelineWithTools:
    """支持工具调用的实时流式处理管道"""

    def __init__(self, verbose: bool = False):
        """
        初始化管道

        Args:
            verbose: 是否显示详细的工具调用信息（默认 False）
        """
        self.text_buffer = ""
        self.stop_event = threading.Event()
        self.verbose = verbose

    def run(
        self,
        llm_stream: Generator[Dict[str, Any], None, None],
        realtime_tts_client,
        streaming_player,
        display_text: bool = True
    ):
        """
        运行实时流式管道（支持工具调用）

        Args:
            llm_stream: LLM 流式输出生成器（来自 chat_stream_with_tools）
            realtime_tts_client: 实时 TTS 客户端
            streaming_player: StreamingAudioPlayer 播放器
            display_text: 是否显示文本

        Returns:
            包含完整文本和指标的字典
        """
        # 启动 TTS 会话
        client_type = type(realtime_tts_client).__name__

        if client_type == "Qwen3RealtimeTTS":
            audio_queue = realtime_tts_client.start_session(
                mode="server_commit",
                audio_format="pcm",
                sample_rate=24000
            )
        elif client_type == "VolcengineRealtimeTTS":
            audio_queue = realtime_tts_client.start_session(
                audio_format="pcm",
                sample_rate=24000
            )
        else:
            audio_queue = realtime_tts_client.start_session()

        # 启动播放器线程
        player_thread = threading.Thread(
            target=streaming_player.play_stream,
            args=(audio_queue, True),
            daemon=True
        )
        player_thread.start()

        print('🤖 学姐: ', end='', flush=True)

        # 从 LLM 读取事件并处理
        full_text = []
        interrupted = False
        tool_calls_count = 0

        try:
            for event in llm_stream:
                # 检查是否被打断
                if self.stop_event.is_set():
                    interrupted = True
                    # 被打断后继续收集文本但不播放
                    if event["type"] == "content":
                        full_text.append(event["data"])
                    continue

                # 处理不同类型的事件
                if event["type"] == "content":
                    # 文本内容
                    chunk = event["data"]

                    # 显示文本
                    if display_text:
                        print(chunk, end='', flush=True)

                    full_text.append(chunk)

                    # 实时发送到 TTS
                    realtime_tts_client.send_text(chunk)
                    time.sleep(0.01)

                elif event["type"] == "tool_call":
                    # 工具调用（完全静默）
                    tool_calls_count += 1
                    # 不显示任何信息

                elif event["type"] == "tool_result":
                    # 工具结果（完全静默）
                    # 不显示任何信息
                    pass

                elif event["type"] == "error":
                    # 错误
                    print(f"\n[❌ {event['data']}]", flush=True)

        except Exception as e:
            print(f'\n❌ 管道错误: {e}')
            import traceback
            traceback.print_exc()

        # 通知 TTS 结束
        realtime_tts_client.finish()

        # 等待 TTS 完成
        if hasattr(realtime_tts_client, 'wait_for_completion'):
            realtime_tts_client.wait_for_completion(timeout=30)

        # 等待播放完成
        player_thread.join(timeout=10)

        # 获取性能指标
        metrics = realtime_tts_client.get_metrics()

        return {
            "text": "".join(full_text),
            "metrics": metrics,
            "interrupted": interrupted,
            "tool_calls_count": tool_calls_count
        }

    def stop(self):
        """停止管道"""
        self.stop_event.set()
