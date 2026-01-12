"""
测试火山引擎 TTS
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tts.volcengine_tts import VolcengineSeed2TTS
from src.config_loader import ConfigLoader
from src.audio.player import AudioPlayer


def test_volcengine_tts():
    """测试火山引擎 TTS"""
    print("="*60)
    print("火山引擎 TTS 测试")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    volcengine_config = config.get("volcengine_seed2", {})

    if not volcengine_config.get("app_id") or not (volcengine_config.get("api_key") or volcengine_config.get("access_token")):
        print("❌ 错误: 未配置火山引擎 API")
        print("\n请在 .env 文件中配置:")
        print("VOLCENGINE_APP_ID=your_app_id")
        print("VOLCENGINE_API_KEY=your_api_key")
        return

    print(f"\n配置信息:")
    print(f"  App ID: {volcengine_config.get('app_id')[:10]}...")
    api_key = volcengine_config.get('api_key') or volcengine_config.get('access_token')
    print(f"  API Key: {api_key[:10]}...")

    # 初始化 TTS
    tts = VolcengineSeed2TTS(
        app_id=volcengine_config.get("app_id"),
        api_key=volcengine_config.get("api_key"),
        access_token=volcengine_config.get("access_token"),
        voice="zh_female_tianmei"  # 甜美女声
    )

    print(f"\n可用音色:")
    for voice in tts.get_available_voices():
        print(f"  - {voice}")

    # 测试文本
    test_texts = [
        "学弟，今天过得怎么样？",
        "这个我之前教过你的，再给你讲一遍吧",
        "真棒！学姐就知道你可以的",
        "哼，下次要记得，不然学姐要生气了"
    ]

    print(f"\n开始测试...")

    for i, text in enumerate(test_texts, 1):
        print(f"\n测试 {i}: {text}")
        output_path = f"data/audios/volcengine_test_{i}.mp3"

        # 确保目录存在
        os.makedirs("data/audios", exist_ok=True)

        # 合成语音
        result = tts.synthesize(text, output_path)

        if result.get("success"):
            print(f"  ✓ 合成成功: {output_path}")

            # 播放音频
            player = AudioPlayer()
            print(f"  🔊 正在播放...")
            play_result = player.play(output_path, blocking=True)

            if play_result.get("success"):
                print(f"  ✓ 播放完成")
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
    print("测试不同音色")
    print("="*60)

    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    volcengine_config = config.get("volcengine_seed2", {})

    if not volcengine_config.get("app_id") or not volcengine_config.get("access_token"):
        print("❌ 错误: 未配置火山引擎 API")
        return

    test_text = "学弟，今天过得怎么样？"

    # 测试不同音色
    voices = [
        ("zh_female_tianmei", "甜美女声"),
        ("zh_female_wanxin", "婉心女声"),
        ("zh_female_qingxin", "清新女声"),
    ]

    player = AudioPlayer()

    for voice_id, voice_name in voices:
        print(f"\n测试音色: {voice_name} ({voice_id})")

        tts = VolcengineSeed2TTS(
            app_id=volcengine_config.get("app_id"),
            api_key=volcengine_config.get("api_key"),
            access_token=volcengine_config.get("access_token"),
            voice=voice_id
        )

        output_path = f"data/audios/volcengine_{voice_id}.mp3"

        result = tts.synthesize(test_text, output_path)

        if result.get("success"):
            print(f"  ✓ 合成成功")
            print(f"  🔊 正在播放...")
            player.play(output_path, blocking=True)
            print(f"  ✓ 播放完成")

            input("\n按回车继续下一个音色...")
        else:
            print(f"  ❌ 失败: {result.get('error')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试火山引擎 TTS")
    parser.add_argument("--voices", action="store_true", help="测试不同音色")

    args = parser.parse_args()

    if args.voices:
        test_different_voices()
    else:
        test_volcengine_tts()
