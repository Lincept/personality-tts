import time
from typing import Dict, List, Any
import statistics

# 从config中导入计时开关配置
from config import ENABLE_TIMER

class Timer:
    """增强版计时模块，专注于语音实时输入输出性能监控"""
    
    def __init__(self):
        self.start_times: Dict[str, float] = {}
        self.end_times: Dict[str, float] = {}
        self.durations: Dict[str, float] = {}
        # 新增：记录多个相同操作的耗时列表
        self.operation_durations: Dict[str, List[float]] = {}
        # 新增：记录音频数据量
        self.audio_data_stats: Dict[str, Dict[str, Any]] = {}
        self.enabled = ENABLE_TIMER
    
    def start(self, name: str, operation_type: str = "") -> None:
        """开始计时，支持操作类型标记"""
        if self.enabled:
            self.start_times[name] = time.time()
            if operation_type and operation_type not in self.operation_durations:
                self.operation_durations[operation_type] = []
    
    def end(self, name: str, operation_type: str = "") -> float:
        """结束计时并返回耗时"""
        if self.enabled and name in self.start_times:
            self.end_times[name] = time.time()
            duration = self.end_times[name] - self.start_times[name]
            self.durations[name] = duration
            
            # 如果是重复操作，记录到操作列表中
            if operation_type:
                self.operation_durations[operation_type].append(duration)
            
            return duration
        return 0.0
    
    def record_audio_data(self, operation: str, data_size: int) -> None:
        """记录音频数据量统计"""
        if self.enabled:
            if operation not in self.audio_data_stats:
                self.audio_data_stats[operation] = {
                    "total_size": 0,
                    "count": 0,
                    "avg_size": 0
                }
            
            stats = self.audio_data_stats[operation]
            stats["total_size"] += data_size
            stats["count"] += 1
            stats["avg_size"] = stats["total_size"] / stats["count"]
    
    def get_duration(self, name: str) -> float:
        """获取指定步骤的耗时"""
        return self.durations.get(name, 0.0)
    
    def get_operation_stats(self, operation_type: str) -> Dict[str, float]:
        """获取操作类型的统计信息"""
        if operation_type not in self.operation_durations or not self.operation_durations[operation_type]:
            return {"avg": 0, "min": 0, "max": 0, "count": 0}
        
        durations = self.operation_durations[operation_type]
        return {
            "avg": statistics.mean(durations),
            "min": min(durations),
            "max": max(durations),
            "count": len(durations)
        }
    
    def print_audio_summary(self) -> None:
        """打印音频数据处理的详细统计"""
        if self.enabled and self.audio_data_stats:
            print("\n=== 音频数据处理统计 ===")
            for operation, stats in self.audio_data_stats.items():
                print(f"{operation}:")
                print(f"  数据块数: {stats['count']}")
                print(f"  总数据量: {stats['total_size']} bytes")
                print(f"  平均数据块大小: {stats['avg_size']:.1f} bytes")
            print("========================")
    
    def print_operation_summary(self) -> None:
        """打印重复操作的统计摘要"""
        if self.enabled and self.operation_durations:
            print("\n=== 实时操作性能统计 ===")
            for operation_type, stats in self.get_all_operation_stats().items():
                print(f"{operation_type}:")
                print(f"  操作次数: {stats['count']}")
                print(f"  平均耗时: {stats['avg']:.4f} 秒")
                print(f"  最小耗时: {stats['min']:.4f} 秒")
                print(f"  最大耗时: {stats['max']:.4f} 秒")
            print("========================")
    
    def get_all_operation_stats(self) -> Dict[str, Dict[str, float]]:
        """获取所有操作类型的统计"""
        return {op: self.get_operation_stats(op) for op in self.operation_durations.keys()}
    
    def print_summary(self) -> None:
        """打印完整的性能摘要"""
        if self.enabled:
            self.print_operation_summary()
            self.print_audio_summary()
            print("\n=== 主要步骤耗时摘要 ===")
            for name, duration in sorted(self.durations.items()):
                print(f"{name}: {duration:.4f} 秒")
            print("==================")
    
    def reset(self) -> None:
        """重置计时器"""
        self.start_times.clear()
        self.end_times.clear()
        self.durations.clear()
        self.operation_durations.clear()
        self.audio_data_stats.clear()

def normalize_messages(messages: Dict) -> List[Dict]:
    target = []
    for _, v in messages.items():
        user_content = (v.get("user") or "").strip()
        assistant_content = (v.get("assistant") or "").strip()
        if not user_content and not assistant_content:
            continue
        if user_content:
            target.append({
                "role": "user",
                "content": user_content
            })
        if assistant_content:
            target.append({
                "role": "assistant",
                "content": assistant_content
            })
    return target

# 创建全局计时器实例
timer = Timer()