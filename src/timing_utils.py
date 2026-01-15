"""
时间统计工具 - 用于性能监控和延迟分析
支持统计各个关键环节的耗时，并提供友好的输出格式
"""
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager


@dataclass
class TimingStats:
    """时间统计数据"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None

    def finish(self):
        """结束计时"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


class ConversationTimer:
    """对话计时器 - 统计一次完整对话的各部分耗时"""

    def __init__(self, enable: bool = True):
        """
        初始化计时器

        Args:
            enable: 是否启用计时
        """
        self.enable = enable
        self.conversation_start: Optional[float] = None
        self.stats: Dict[str, TimingStats] = {}
        self.conversation_id: int = 0

    def start_conversation(self):
        """开始一次新的对话"""
        if not self.enable:
            return
        self.conversation_id += 1
        self.conversation_start = time.time()
        self.stats = {}

    def start(self, name: str) -> Optional[TimingStats]:
        """
        开始计时某个环节

        Args:
            name: 环节名称

        Returns:
            TimingStats 对象（如果启用计时）
        """
        if not self.enable:
            return None

        stat = TimingStats(name=name, start_time=time.time())
        self.stats[name] = stat
        return stat

    def end(self, name: str):
        """
        结束计时某个环节

        Args:
            name: 环节名称
        """
        if not self.enable or name not in self.stats:
            return

        self.stats[name].finish()

    @contextmanager
    def time(self, name: str):
        """
        上下文管理器 - 自动计时

        Args:
            name: 环节名称

        Usage:
            with timer.time("LLM生成"):
                # 执行操作
        """
        stat = self.start(name)
        try:
            yield stat
        finally:
            if stat:
                stat.finish()

    def get_total_duration(self) -> Optional[float]:
        """获取对话总耗时"""
        if not self.enable or not self.conversation_start:
            return None
        return time.time() - self.conversation_start

    def get_summary(self) -> Optional[Dict]:
        """
        获取统计摘要

        Returns:
            包含各环节耗时的字典
        """
        if not self.enable:
            return None

        total_duration = self.get_total_duration()

        summary = {
            "conversation_id": self.conversation_id,
            "total_duration": total_duration,
            "breakdown": {}
        }

        for name, stat in self.stats.items():
            summary["breakdown"][name] = {
                "duration": stat.duration,
                "percentage": (stat.duration / total_duration * 100) if total_duration else 0
            }

        return summary

    def print_summary(self):
        """打印友好的统计摘要"""
        if not self.enable:
            return

        summary = self.get_summary()
        if not summary:
            return

        total = summary["total_duration"]

        print()
        print("=" * 60)
        print(f"📊 对话 #{summary['conversation_id']} 性能统计")
        print("=" * 60)
        print(f"⏱️  总耗时: {total:.3f} 秒")
        print()

        print("各环节耗时:")
        print("-" * 60)

        # 分类显示时间统计
        memory_stats = []
        llm_stats = []
        tts_stats = []

        for name, data in summary["breakdown"].items():
            duration = data["duration"]
            percentage = data["percentage"]
            bar_length = int(percentage / 2)
            bar = "█" * bar_length

            # 分类
            if name in ["意图分析", "记忆检索"]:
                memory_stats.append((name, duration, percentage, bar))
            elif name in ["LLM生成", "LLM流式生成"]:
                llm_stats.append((name, duration, percentage, bar))
            elif name in ["TTS处理", "TTS首字延迟", "TTS总时长"]:
                tts_stats.append((name, duration, percentage, bar))
            else:
                # 其他指标（如音频块数）
                if name == "TTS音频块数":
                    print(f"  {name:20s} {duration:6.0f}  块")

        # 打印记忆相关统计
        if memory_stats:
            print("📝 记忆管理:")
            for name, duration, percentage, bar in memory_stats:
                warning = ""
                if duration > 1:
                    warning = " 🔴"
                elif duration > 0.5:
                    warning = " 🟡"
                print(f"  {name:20s} {duration:6.3f}s  {percentage:5.1f}%  {bar}{warning}")
            print()

        # 打印 LLM 相关统计
        if llm_stats:
            print("🧠 LLM 处理:")
            for name, duration, percentage, bar in llm_stats:
                warning = ""
                if duration > 3:
                    warning = " 🔴"
                elif duration > 2:
                    warning = " 🟡"
                print(f"  {name:20s} {duration:6.3f}s  {percentage:5.1f}%  {bar}{warning}")
            print()

        # 打印 TTS 相关统计
        if tts_stats:
            print("🔊 TTS 处理:")
            for name, duration, percentage, bar in tts_stats:
                warning = ""
                if duration > 2:
                    warning = " 🔴"
                elif duration > 1:
                    warning = " 🟡"
                print(f"  {name:20s} {duration:6.3f}s  {percentage:5.1f}%  {bar}{warning}")
            print()

        print("-" * 60)
        print()

        # 分析瓶颈
        if summary["breakdown"]:
            # 过滤掉非时间指标
            time_stats = {k: v for k, v in summary["breakdown"].items()
                        if k not in ["TTS音频块数"]}

            if time_stats:
                max_duration = max(data["duration"] for data in time_stats.values())
                bottleneck = [name for name, data in time_stats.items() if data["duration"] == max_duration]
                if bottleneck and max_duration > 1:
                    print(f"💡 瓶颈分析: {bottleneck[0]} 耗时最长 ({max_duration:.3f}s)")
                    print()

    def reset(self):
        """重置计时器"""
        self.conversation_start = None
        self.stats = {}
