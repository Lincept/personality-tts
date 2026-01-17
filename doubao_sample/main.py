import asyncio
import argparse

import config
from audio_manager import DialogSession
from logging_setup import setup_log_recording

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
    # 可选：将运行日志写入 log/（不影响控制台输出）
    # 在导入/运行其它逻辑前尽早启用，确保异常 traceback 也会被记录。
    try:
        setup_log_recording(
            log_to_file=getattr(config, "LOG_TO_FILE", False),
            log_dir=getattr(config, "LOG_DIR", "log"),
            log_file=getattr(config, "LOG_FILE", "console.log"),
        )
    except Exception:
        pass
    asyncio.run(main())