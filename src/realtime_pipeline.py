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
            realtime_tts_client: Qwen3RealtimeTTS 客户端
            streaming_player: StreamingAudioPlayer 播放器
            display_text: 是否显示文本
        """
        # 启动 TTS 会话
        audio_queue = realtime_tts_client.start_session(
            mode="server_commit",  # 服务端自动断句
            audio_format="pcm",
            sample_rate=24000
        )

        # 启动播放器线程
        player_thread = threading.Thread(
            target=streaming_player.play_stream,
            args=(audio_queue, True),
            daemon=True
        )
        player_thread.start()

        print('\n🤖 AI 回复 (实时流式):')
        print('-' * 60)

        # 从 LLM 读取文本并实时发送到 TTS
        full_text = []
        try:
            for chunk in llm_stream:
                if self.stop_event.is_set():
                    break

                # 显示文本
                if display_text:
                    print(chunk, end='', flush=True)

                full_text.append(chunk)

                # 实时发送到 TTS（Prompt 已经控制不输出格式符号）
                realtime_tts_client.send_text(chunk)

                # 小延迟，避免发送过快
                time.sleep(0.01)

        except Exception as e:
            print(f'\n[管道错误] LLM 流式输出: {e}')

        # 通知 TTS 结束
        realtime_tts_client.finish()

        print('\n' + '-' * 60)
        print('[管道] LLM 输出完成，等待 TTS 和播放完成...')

        # 等待 TTS 完成
        realtime_tts_client.wait_for_completion(timeout=30)

        # 等待播放完成
        player_thread.join(timeout=10)

        # 获取性能指标
        metrics = realtime_tts_client.get_metrics()
        print(f'\n[性能指标]')
        print(f'  会话 ID: {metrics.get("session_id")}')
        print(f'  首音频延迟: {metrics.get("first_audio_delay", 0):.3f}秒')
        print(f'  总文本长度: {len("".join(full_text))} 字符')

        return {
            "text": "".join(full_text),
            "metrics": metrics
        }

    def stop(self):
        """停止管道"""
        self.stop_event.set()
