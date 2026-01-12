"""
测试火山引擎 Seed2 TTS WebSocket 双向流式
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tts.volcengine_websocket_tts import VolcengineWebSocketTTS
from src.config_loader import ConfigLoader
from src.audio.player import AudioPlayer


def test_websocket_tts():
    """测试火山引擎 WebSocket TTS"""
    print("="*60)
    print("火山引擎 Seed2 TTS WebSocket 双向流式测试")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    volcengine_config = config.get("volcengine_seed2", {})

    if not volcengine_config.get("app_id") or not (volcengine_config.get("api_key") or volcengine_config.get("access_token")):
        print("❌ 错误: 未配置火山引擎 API")
        print("\n请在 .env 文件中配置:")
        print("VOLCENGINE_APP_ID=your_app_id")
        print("VOLCENGINE_ACCESS_TOKEN=your_access_token")
        return

    print(f"\n配置信息:")
    print(f"  App ID: {volcengine_config.get('app_id')}")
    access_token = volcengine_config.get('access_token') or volcengine_config.get('api_key')
    print(f"  Access Token: {access_token[:20] if access_token else 'N/A'}...")
    print(f"  连接方式: WebSocket 双向流式")

    # 初始化 TTS
    tts = VolcengineWebSocketTTS(
        app_id=volcengine_config.get("app_id"),
        api_key=volcengine_config.get("api_key"),
        access_token=volcengine_config.get("access_token"),
        voice="zh_female_cancan_mars_bigtts"  # Mars BigTTS 音色
    )

    # 测试文本
    test_texts = [
        "学弟，今天过得怎么样？",
        "这个我之前教过你的，再给你讲一遍吧",
        "真棒！学姐就知道你可以的",
    ]

    print(f"\n开始测试...")

    for i, text in enumerate(test_texts, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}/{len(test_texts)}: {text}")
        print(f"{'='*60}")

        output_path = f"data/audios/volcengine_ws_test_{i}.mp3"

        # 确保目录存在
        os.makedirs("data/audios", exist_ok=True)

        # 合成语音
        print(f"  🔄 正在通过 WebSocket 合成语音...")
        result = tts.synthesize(text, output_path)

        if result.get("success"):
            print(f"  ✅ 合成成功!")
            print(f"     文件: {output_path}")
            print(f"     文本长度: {result.get('text_length')} 字符")
            print(f"     音频大小: {result.get('audio_size')} 字节")
            print(f"     音色: {result.get('voice')}")

            # 播放音频
            player = AudioPlayer()
            print(f"  🔊 正在播放...")
            play_result = player.play(output_path, blocking=True)

            if play_result.get("success"):
                print(f"  ✅ 播放完成")
            else:
                print(f"  ❌ 播放失败: {play_result.get('error')}")
        else:
            print(f"  ❌ 合成失败: {result.get('error')}")
            print(f"\n详细错误信息:")
            print(f"  {result}")
            break

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


def test_different_voices():
    """测试不同音色"""
    print("\n" + "="*60)
    print("测试不同音色 (WebSocket)")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    volcengine_config = config.get("volcengine_seed2", {})

    if not volcengine_config.get("app_id") or not (volcengine_config.get("api_key") or volcengine_config.get("access_token")):
        print("❌ 错误: 未配置火山引擎 API")
        return

    test_text = "学弟，今天过得怎么样？"

    # 测试不同音色
    voices = [
        ("zh_female_cancan_mars_bigtts", "灿灿女声"),
        ("zh_male_aojiaobazong_mars_bigtts", "霸总男声"),
        ("zh_female_wanwanxiaohe_mars_bigtts", "婉婉小和"),
        ("zh_male_qingxinnansheng_mars_bigtts", "清新男声"),
    ]

    player = AudioPlayer()

    for voice_id, voice_name in voices:
        print(f"\n{'='*60}")
        print(f"测试音色: {voice_name} ({voice_id})")
        print(f"{'='*60}")

        tts = VolcengineWebSocketTTS(
            app_id=volcengine_config.get("app_id"),
            api_key=volcengine_config.get("api_key"),
            access_token=volcengine_config.get("access_token"),
            voice=voice_id
        )

        output_path = f"data/audios/volcengine_ws_{voice_id}.mp3"

        print(f"  🔄 正在合成...")
        result = tts.synthesize(test_text, output_path)

        if result.get("success"):
            print(f"  ✅ 合成成功")
            print(f"  🔊 正在播放...")
            player.play(output_path, blocking=True)
            print(f"  ✅ 播放完成")

            input("\n按回车继续下一个音色...")
        else:
            print(f"  ❌ 失败: {result.get('error')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试火山引擎 WebSocket TTS")
    parser.add_argument("--voices", action="store_true", help="测试不同音色")

    args = parser.parse_args()

    if args.voices:
        test_different_voices()
    else:
        test_websocket_tts()
