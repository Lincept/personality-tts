"""doubao_sample.logging_setup

为 doubao_sample 提供一个简单的“可选落盘”能力：
- 默认不写文件
- 开启后将 stdout/stderr tee 到 log/ 目录下，方便保留运行日志

环境变量（在 doubao_sample/.env 中配置）：
- DOUBAO_LOG_TO_FILE: true/false，是否写入 log 文件夹（默认 false）
- DOUBAO_LOG_DIR: 日志目录（默认 log）
- DOUBAO_LOG_FILE: tee 文件名（默认 console.log）
- DOUBAO_LOG_TEE_STDIO: true/false，是否 tee stdout/stderr（默认 true，当 LOG_TO_FILE 开启时）
"""

from __future__ import annotations

import atexit
import os
import sys
from typing import Optional, TextIO


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


class _TeeStream:
    def __init__(self, original: TextIO, file_handle: TextIO):
        self._original = original
        self._file = file_handle

    def write(self, s: str) -> int:
        n = 0
        try:
            n = self._original.write(s)
        except Exception:
            pass
        try:
            self._file.write(s)
        except Exception:
            pass
        return n

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass
        try:
            self._file.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        try:
            return bool(getattr(self._original, "isatty")())
        except Exception:
            return False

    @property
    def encoding(self) -> str:
        return getattr(self._original, "encoding", "utf-8")


def setup_log_recording(
    *,
    log_to_file: Optional[bool] = None,
    log_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    tee_stdio: Optional[bool] = None,
) -> Optional[str]:
    """根据配置决定是否将 stdout/stderr 记录到 log 文件。

    - 参数为 None 时回退到环境变量
    - 返回 tee 文件路径；未开启时返回 None
    """
    if log_to_file is None:
        log_to_file = _env_bool("DOUBAO_LOG_TO_FILE", default=False)
    if not log_to_file:
        return None

    if tee_stdio is None:
        tee_stdio = _env_bool("DOUBAO_LOG_TEE_STDIO", default=True)
    if not tee_stdio:
        return None

    if log_dir is None:
        log_dir = os.getenv("DOUBAO_LOG_DIR", "log")
    if log_file is None:
        log_file = os.getenv("DOUBAO_LOG_FILE", "console.log")

    log_dir = str(log_dir).strip() or "log"
    log_file = str(log_file).strip() or "console.log"

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    # line-buffered: 尽量实时落盘
    f = open(log_path, "a", encoding="utf-8", buffering=1)

    # 避免重复包装
    if not isinstance(sys.stdout, _TeeStream):
        sys.stdout = _TeeStream(sys.stdout, f)  # type: ignore[assignment]
    if not isinstance(sys.stderr, _TeeStream):
        sys.stderr = _TeeStream(sys.stderr, f)  # type: ignore[assignment]

    @atexit.register
    def _close_file() -> None:
        try:
            f.flush()
        except Exception:
            pass
        try:
            f.close()
        except Exception:
            pass

    return log_path
