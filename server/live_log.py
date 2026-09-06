"""全局实时日志注册表 — 供任意模块写入/读取任务级别的实时日志。"""
from __future__ import annotations

import threading

# task_id -> list[str]
_live_buffers: dict[str, list[str]] = {}
_lock = threading.Lock()


def init(task_id: str) -> None:
    """初始化指定任务的日志缓冲区（清空旧数据）。"""
    with _lock:
        _live_buffers[task_id] = []


def write(task_id: str, line: str) -> None:
    """写入一行实时日志到指定任务的缓冲区。"""
    with _lock:
        buf = _live_buffers.get(task_id)
        if buf is None:
            buf = []
            _live_buffers[task_id] = buf
        buf.append(line)
        if len(buf) > 2000:
            buf[:500] = []


def read(task_id: str, tail: int = 200) -> str:
    """读取指定任务缓冲区的最近 tail 行。"""
    with _lock:
        buf = _live_buffers.get(task_id)
        if not buf:
            return ""
        lines = buf[-tail:] if tail < len(buf) else buf
        return "".join(lines)


def cleanup(task_id: str) -> None:
    """清理指定任务的缓冲区（任务结束后调用）。"""
    with _lock:
        _live_buffers.pop(task_id, None)
