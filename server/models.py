"""共享数据模型 — 任务状态、执行结果等。

TaskRecord 是所有异步操作的核心数据结构：
- 由 TaskScheduler.submit() 创建，自动生成唯一 ID
- 后台线程通过修改其 status/result/steps 报告进度
- 控制台通过 GET /api/tasks/<id> 读取其状态
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """任务状态枚举 — 继承 str 以便直接 JSON 序列化。"""
    PENDING = "pending"    # 已提交，等待执行
    RUNNING = "running"    # 正在执行中
    SUCCESS = "success"    # 执行成功
    FAILED = "failed"      # 执行失败


@dataclass
class TaskRecord:
    """任务记录 — 跟踪单个异步操作的完整生命周期。"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: Any = None
    error: str | None = None
    steps: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """序列化为字典，供 API 接口返回。"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "steps": self.steps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskRecord":
        """从持久化字典恢复（历史回填用）。"""
        task = cls()
        task.id = data.get("id") or task.id
        task.name = data.get("name", "")
        try:
            task.status = TaskStatus(data.get("status", TaskStatus.PENDING.value))
        except ValueError:
            task.status = TaskStatus.PENDING
        task.created_at = data.get("created_at") or task.created_at
        task.started_at = data.get("started_at")
        task.finished_at = data.get("finished_at")
        task.result = data.get("result")
        task.error = data.get("error")
        task.steps = data.get("steps", [])
        return task
