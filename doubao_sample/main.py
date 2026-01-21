import sys
import asyncio
import argparse

from audio_manager import DialogSession
from logging_setup import setup_log_recording

async def main() -> None:
    parser = argparse.ArgumentParser(description="Real-time Dialog Client")
    parser.add_argument("--format", type=str, choices=["pcm", "pcm_s16le"], default="pcm", help="The audio format (e.g., pcm, pcm_s16le).")
    parser.add_argument("--mod", type=str, choices=["keep_alive", "text"], default="keep_alive", help="Use mod to select plain text input mode or keep_alive mode, the default is keep_alive mode")
    parser.add_argument("--audio-file", type=str, default="", help="audio file send to server, if not set, will use microphone input.")
    parser.add_argument("--memory", type=str, choices=["none", "mem0", "viking"], default="none", help="Memory backend to use (e.g., none, mem0, viking).")
    parser.add_argument("--aec", action="store_true", help="Enable AEC (Acoustic Echo Cancellation) for audio processing")

    args = parser.parse_args()

    # 创建音频管理器实例
    session = DialogSession(
        output_audio_format=args.format,
        audio_file_path=args.audio_file,
        mod=args.mod,
        memory_backend=args.memory,
        use_aec=args.aec
    )
    await session.start()

if __name__ == "__main__":
    try:
        setup_log_recording()
    except Exception as e:
        print(f"日志系统初始化失败: {e}", file=sys.stderr)
    asyncio.run(main())