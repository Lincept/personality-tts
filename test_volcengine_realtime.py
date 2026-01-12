"""
测试火山引擎实时流式 TTS
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tts.volcengine_realtime_tts import VolcengineRealtimeTTS
from src.audio.streaming_player import StreamingAudioPlayer
from src.config_loader import ConfigLoader
import time


def test_volcengine_realtime():
    """测试火山引擎实时 TTS"""
    print("="*60)
    print("火山引擎实时流式 TTS 测试")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()
    volcengine_config = config.get("volcengine_seed2", {})

    app_id = volcengine_config.get("app_id")
    access_token = volcengine_config.get("access_token") or volcengine_config.get("api_key")

    if not app_id or not access_token:
        print("❌ 错误: 未配置火山引擎 API")
        return

    print(f"\n配置信息:")
    print(f"  App ID: {app_id}")
    print(f"  Access Token: {access_token[:20]}...")
    print(f"  音色: zh_female_cancan_mars_bigtts")

    # 创建实时 TTS 客户端
    tts = VolcengineRealtimeTTS(
        app_id=app_id,
        access_token=access_token,
        voice="zh_female_cancan_mars_bigtts"
    )

    # 创建流式播放器
    player = StreamingAudioPlayer(
        sample_rate=24000,
        format="mp3"
    )

    # 测试文本
    test_texts = [
        "学弟，",
        "今天",
        "过得",
        "怎么样？",
    ]

    print("\n开始测试...")
    print("="*60)

    try:
        # 启动会话
        audio_queue = tts.start_session()

        # 启动播放器（非阻塞）
        player.play_stream(audio_queue, blocking=False)

        # 逐个发送文本
        for i, text in enumerate(test_texts, 1):
            print(f"发送文本 {i}/{len(test_texts)}: {text}")
            tts.send_text(text)
            time.sleep(0.5)  # 模拟流式输入

        # 结束会话
        print("\n结束会话...")
        tts.finish()

        # 等待播放完成
        print("等待播放完成...")
        time.sleep(5)

        # 获取性能指标
        metrics = tts.get_metrics()
        print(f"\n性能指标:")
        print(f"  会话 ID: {metrics.get('session_id')}")
        print(f"  首音频延迟: {metrics.get('first_audio_delay', 0):.3f}秒")
        print(f"  音色: {metrics.get('voice')}")

        print("\n✅ 测试成功!")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 断开连接
        tts.disconnect()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    test_volcengine_realtime()
