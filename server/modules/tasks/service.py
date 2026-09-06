"""任务编排业务逻辑 — 提交、执行、查询、取消异步任务。

TaskScheduler 是所有异步操作的统一入口。
通过 submit() 提交任务后，系统在后台 daemon 线程中执行，
控制台通过 task_id 轮询状态或调用 cancel() 中止执行。

演示版：执行函数由调用方提供（内部组合 DemoEngine 步骤），
调度器本身与具体执行内容解耦。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable

from core.logging_config import get_logger

from server.models import TaskRecord, TaskStatus

logger = get_logger(__name__)


_scheduler: TaskScheduler | None = None


def get_scheduler() -> "TaskScheduler":
    """全局调度器单例（延迟创建，供跨模块复用）。"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


class TaskScheduler:
    """异步任务调度器 — 管理所有后台任务的生命周期。"""

    def __init__(self):
        self._tasks: dict[str, TaskRecord] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def get_task(self, task_id: str) -> TaskRecord | None:
        """根据 ID 获取单个任务记录。"""
        with self._lock:
            return self._tasks.get(task_id)

    def find_task_by_prefix(self, prefix: str) -> str | None:
        """根据前 8 位前缀查找完整 task_id。"""
        if len(prefix) >= 12:
            return prefix
        with self._lock:
            for tid in self._tasks:
                if tid.startswith(prefix):
                    return tid
        return None

    def list_tasks(self, limit: int = 50, status: str | None = None) -> list[dict]:
        """获取任务列表（按创建时间倒序）。"""
        with self._lock:
            tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
            if status:
                tasks = [t for t in tasks if t.status.value == status]
            return [t.to_dict() for t in tasks[:limit]]

    def submit(self, name: str, fn: Callable[[TaskRecord], None],
               platform: str = "", cases: list[str] | None = None) -> TaskRecord:
        """提交一个异步任务。

        Args:
            name: 任务名称
            fn: 任务执行函数，接收 TaskRecord，负责更新 status/result
            platform: 平台 key（用于远程索引与列表展示）
            cases: 用例路径列表
        """
        task = TaskRecord(name=name)
        task.platform = platform  # type: ignore[attr-defined]
        task.cases = cases or []  # type: ignore[attr-defined]
        cancel_event = threading.Event()

        logger.info("提交任务: id=%s, name=%s", task.id, name)

        with self._lock:
            self._tasks[task.id] = task
            self._cancel_events[task.id] = cancel_event

        # 把 cancel_event 挂到任务上，执行函数里通过它响应取消
        task.cancel_event = cancel_event  # type: ignore[attr-defined]

        thread = threading.Thread(target=self._execute, args=(task, fn), daemon=True)
        self._threads[task.id] = thread
        thread.start()
        return task

    def cancel(self, task_id: str) -> dict:
        """取消正在执行的任务。"""
        with self._lock:
            task = self._tasks.get(task_id)
            cancel_event = self._cancel_events.get(task_id)

        if task is None:
            return {"success": False, "message": "任务不存在"}

        if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            return {"success": False, "message": f"任务已结束，状态为 {task.status.value}"}

        logger.info("取消任务: id=%s, name=%s", task_id, task.name)
        if cancel_event:
            cancel_event.set()
        task.status = TaskStatus.FAILED
        task.error = "用户取消"
        task.finished_at = time.time()
        return {"success": True, "message": f"任务 {task_id} 已标记为取消"}

    def _execute(self, task: TaskRecord, fn: Callable[[TaskRecord], None]):
        """后台线程执行任务函数。"""
        logger.info("开始执行任务: id=%s, name=%s", task.id, task.name)
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        try:
            cancel_event = getattr(task, "cancel_event", None)
            if cancel_event is not None and cancel_event.is_set():
                return
            fn(task)
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.SUCCESS
            logger.info("任务执行完成: id=%s, status=%s", task.id, task.status.value)
        except Exception as e:
            logger.error("任务执行异常: id=%s, error=%s", task.id, e, exc_info=True)
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
            task.error = str(e)
        finally:
            if task.finished_at is None:
                task.finished_at = time.time()
            _persist_history(task)


# ---------------------------------------------------------------- 历史持久化

def _history_dir(project_root) -> Path:
    return Path(project_root) / "var" / "data" / "task_history"


def _persist_history(task: TaskRecord) -> None:
    """任务结束后追加一条摘要到 JSONL，供重启后任务列表仍有历史数据。"""
    try:
        from server import runtime
        d = _history_dir(runtime.project_root())
        d.mkdir(parents=True, exist_ok=True)
        line = {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
            "error": task.error,
            "steps": task.steps,
            "result": task.result,
            "platform": getattr(task, "platform", ""),
            "cases": getattr(task, "cases", []),
        }
        with open(d / "tasks.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        logger.exception("任务历史持久化失败")


def load_history(project_root, limit: int = 200) -> list[dict]:
    """读取持久化的历史任务（旧→新），供 scheduler 冷启动时回填。"""
    d = _history_dir(project_root)
    if not d.exists():
        return []
    try:
        lines = (d / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
