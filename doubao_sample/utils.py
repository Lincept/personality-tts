import time
from typing import Dict

class Timer:
    def __init__(self):
        self.timers: Dict[str, float] = {}
        self.elapsed_times: Dict[str, float] = {}
    
    def start(self, name: str) -> None:
        self.timers[name] = time.time()
    
    def end(self, name: str) -> float:
        if name in self.timers:
            elapsed = time.time() - self.timers[name]
            del self.timers[name]
            self.elapsed_times[name] = elapsed
            return elapsed
        return 0.0
    
    def print_summary(self) -> None:
        if self.elapsed_times:
            print("Timer Summary:")
            for name, elapsed in self.elapsed_times.items():
                print(f"  {name}: {elapsed:.3f}s")


timer = Timer()
