import asyncio
import argparse

import config
from audio_manager import DialogSession

async def main() -> None:
    parser = argparse.ArgumentParser(description="Real-time Dialog Client")
    parser.add_argument("--format", type=str, default="pcm", help="The audio format (e.g., pcm, pcm_s16le).")
    parser.add_argument("--mod", type=str, choices=["audio", "text"], default="audio", help="Use mod to select plain text input mode or audio mode, the default is audio mode")
    parser.add_argument("--audio", type=str, default="", help="audio file send to server, if not set, will use microphone input.")
    parser.add_argument("--recv_timeout", type=int, default=10, help="Timeout for receiving messages,value range [10,120]")
    parser.add_argument("--memory", action="store_true", help="Use memory or not, if not set, will be True")

    args = parser.parse_args()

    # 创建音频管理器实例
    session = DialogSession(ws_config=config.ws_connect_config, output_audio_format=args.format, audio_file_path=args.audio,mod=args.mod,recv_timeout=args.recv_timeout,use_memory=args.memory)
    await session.start()

if __name__ == "__main__":
    asyncio.run(main())