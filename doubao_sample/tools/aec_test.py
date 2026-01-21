"""macOS 语音处理(AEC) + 录音测试脚本。

核心功能：
- 启用 AVAudioInputNode 的 Voice Processing（硬件/系统级回声消除）
- 通过 Tap 抓取麦克风音频并保存为 WAV
- 远端音频（或测试音频）从 AVAudioPlayerNode 播放，以便 AEC 生效

运行示例：
    python tools/aec_test.py
    python tools/aec_test.py --play path/to/test.wav
"""

from __future__ import annotations

import argparse
import time
import wave
from pathlib import Path

import numpy as np
import AVFoundation

class VoiceEngine:
    def __init__(self, *, buffer_size: int = 1024):
        self.engine = AVFoundation.AVAudioEngine.alloc().init()
        self.input_node = self.engine.inputNode()
        self.output_node = self.engine.outputNode()
        self.player_node = AVFoundation.AVAudioPlayerNode.alloc().init()

        self.buffer_size = int(buffer_size)

        # 用于保存录音数据（float32, [-1, 1]）
        self.recorded_frames: list[np.ndarray] = []
        self.sample_rate: int = 0

        self._enable_voice_processing()

        # 获取输入节点的硬件格式：录音 tap 和保存 WAV 时以此采样率为准
        self.hw_format = self.input_node.inputFormatForBus_(0)
        self.sample_rate = int(self.hw_format.sampleRate())

        self._install_input_tap()
        self._setup_playback_chain()

    def _enable_voice_processing(self) -> None:
        """开启系统级 Voice Processing（AEC 等）。"""
        try:
            success, err = self.input_node.setVoiceProcessingEnabled_error_(True, None)
        except AttributeError:
            raise RuntimeError("当前 macOS / PyObjC 不支持 setVoiceProcessingEnabled。")

        if not success:
            raise RuntimeError(f"启用 Voice Processing 失败: {err}")

        print("✅ 硬件回声消除 (Voice Processing/VPIO) 已开启")

    def _install_input_tap(self) -> None:
        """安装 Tap，把麦克风音频抓出来存入内存。"""

        def input_callback(buffer, when):
            self._handle_input_buffer(buffer)

        self.input_node.installTapOnBus_bufferSize_format_block_(
            0,  # Bus 0 是输入
            self.buffer_size,
            self.hw_format,
            input_callback,
        )

    def _handle_input_buffer(self, buffer) -> None:
        frame_length = int(buffer.frameLength())
        if frame_length <= 0:
            return

        fmt = buffer.format()
        channel_count = int(fmt.channelCount())
        channel_data = buffer.floatChannelData()
        if not channel_data:
            return

        try:
            # channel_data[ch] 是一个 float* 指针；在 PyObjC 下可按索引读取。
            if channel_count <= 1:
                audio = np.array([channel_data[0][i] for i in range(frame_length)], dtype=np.float32)
            else:
                channels = [
                    np.array([channel_data[ch][i] for i in range(frame_length)], dtype=np.float32)
                    for ch in range(channel_count)
                ]
                audio = np.mean(np.stack(channels, axis=0), axis=0).astype(np.float32)

            self.recorded_frames.append(audio)
        except Exception as e:
            print(f"录音数据处理错误: {e}")

    def _setup_playback_chain(self) -> None:
        """配置播放链路：远端声音需要从 player_node 播放，AEC 才能识别回声路径。"""
        self.engine.attachNode_(self.player_node)
        self.engine.connect_to_fromBus_toBus_format_(
            self.player_node,
            self.engine.mainMixerNode(),
            0,
            0,
            self.hw_format,
        )

    def start(self):
        success, err = self.engine.startAndReturnError_(None)
        if not success:
            raise RuntimeError(f"启动 Audio Engine 失败: {err}")
        print("✅ Audio Engine 已启动")

    def stop(self):
        try:
            # 先移除 tap，避免 stop 时仍有回调进入
            self.input_node.removeTapOnBus_(0)
        except Exception:
            pass

        try:
            self.player_node.stop()
        except Exception:
            pass

        self.engine.stop()
        self.save_recording()
        print("Audio Engine 已停止")

    def save_recording(self):
        """保存录音到文件"""
        if not self.recorded_frames or self.sample_rate == 0:
            print("没有录音数据")
            return
        
        # 合并所有音频帧
        audio_data = np.concatenate(self.recorded_frames)
        
        if len(audio_data) == 0:
            print("没有有效的录音数据")
            return
        
        # 转换为 int16 格式（保险起见做 clip）
        audio_data = np.clip(audio_data, -1.0, 1.0)
        audio_int16 = (audio_data * 32767.0).astype(np.int16)
        
        # 保存为 wav 文件
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"aec_test_{int(time.time())}.wav"
        
        with wave.open(str(output_file), 'wb') as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        
        print(f"✅ 录音已保存到: {output_file}")

    def play_test_audio(self, audio_file):
        """播放测试音频文件"""
        try:
            audio_path = Path(audio_file)
            if not audio_path.exists():
                print(f"❌ 文件不存在: {audio_path}")
                return

            file_url = AVFoundation.NSURL.fileURLWithPath_(str(audio_path))
            audio_file_obj, err = AVFoundation.AVAudioFile.alloc().initForReading_error_(file_url, None)
            if err:
                print(f"❌ 读取音频文件失败: {err}")
                return

            frame_capacity = int(audio_file_obj.length())
            buffer = AVFoundation.AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(
                audio_file_obj.processingFormat(),
                frame_capacity,
            )
            success, err = audio_file_obj.readIntoBuffer_error_(buffer, None)
            if not success:
                print(f"❌ 读取音频失败: {err}")
                return

            self.player_node.scheduleBuffer_completionHandler_(buffer, None)
            if not self.player_node.isPlaying():
                self.player_node.play()
            print(f"🔊 正在播放: {audio_path}")
        except Exception as e:
            print(f"❌ 播放失败: {e}")

    def play_remote_audio(self, pcm_buffer):
        """播放远端传来的音频（pcm_buffer: AVAudioPCMBuffer）。"""
        self.player_node.scheduleBuffer_completionHandler_(pcm_buffer, None)
        if not self.player_node.isPlaying():
            self.player_node.play()

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="macOS AEC(Voice Processing) + 录音测试")
    parser.add_argument(
        "--play",
        type=str,
        default=None,
        help="启动后播放一个测试音频文件（让 AEC 有远端回声源）",
    )
    parser.add_argument(
        "--buffer-size",
        type=int,
        default=1024,
        help="输入 Tap buffer 大小（默认 1024）",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    voip_app = VoiceEngine(buffer_size=args.buffer_size)
    voip_app.start()

    print("✅ 回声消除测试程序已启动")
    print("💡 使用方法:")
    print("   1) 对着麦克风说话，同时在系统里播放音乐/视频测试回声消除")
    print("   2) 或用 --play 播放一个测试音频作为远端声音")
    print("   3) 按 Ctrl+C 退出并保存录音")
    print()

    if args.play:
        voip_app.play_test_audio(args.play)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止...")
        voip_app.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())