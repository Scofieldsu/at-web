"""任务编排模块 — 管理异步任务生命周期。

提供以下能力：
- 查询所有任务列表（支持按状态筛选）
- 查询单个任务详情
- 取消正在执行的任务
- "远程"任务提交/状态/日志/移除（演示版：远程机即本机）

任务 ID 在提交时自动生成（12位随机hex），控制台通过此 ID 进行后续操作。
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from server import live_log
from server.models import TaskRecord, TaskStatus

from .service import TaskScheduler, get_scheduler, load_history

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


def _warm_history(project_root: str | None = None) -> None:
    """冷启动时把持久化历史回填到内存（只读展示用，幂等）。"""
    root = Path(project_root or current_app.config["PROJECT_ROOT"])
    items = load_history(root)
    if not items:
        return
    with get_scheduler()._lock:  # noqa: SLF001
        existing = set(get_scheduler()._tasks.keys())  # noqa: SLF001
    for item in items:
        if item["id"] in existing:
            continue
        task = TaskRecord.from_dict(item)  # type: ignore[attr-defined]
        with get_scheduler()._lock:  # noqa: SLF001
            get_scheduler()._tasks[task.id] = task  # noqa: SLF001


@bp.route("/demo", methods=["POST"])
def demo():
    """演示接口：提交一个 2 秒后完成的假任务。"""
    import threading

    def fake_work(task):
        task.steps.append({"name": "fake_step", "status": "running"})
        for _ in range(10):
            if getattr(task, "cancel_event", None) and task.cancel_event.is_set():
                return
            time.sleep(0.2)
        task.steps[-1]["status"] = "success"

    task = get_scheduler().submit("demo-task", fake_work)
    return jsonify({"task_id": task.id,
                    "message": "演示任务已提交，通过 GET /api/tasks/<task_id> 轮询结果"}), 202


@bp.route("/", methods=["GET"])
def list_tasks():
    """获取任务列表。Query: limit(默认50), status"""
    limit = request.args.get("limit", 50, type=int)
    status = request.args.get("status")
    return jsonify(get_scheduler().list_tasks(limit, status=status))


@bp.route("/app-log", methods=["GET"])
def get_app_log():
    """获取服务端 app.log 内容。Query: ?tail=<行数>"""
    project_root = Path(current_app.config["PROJECT_ROOT"])
    log_dir = current_app.config.get("LOG_DIR", "var/logs")
    log_file = current_app.config.get("LOG_FILE", "app.log")
    log_path = project_root / log_dir / log_file

    tail = request.args.get("tail", 0, type=int)
    if not log_path.exists():
        return jsonify({"error": "日志文件不存在"}), 404

    if tail > 0:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail_lines = lines[-tail:] if tail < len(lines) else lines
        return "\n".join(tail_lines), 200, {"Content-Type": "text/plain; charset=utf-8"}

    return log_path.read_text(encoding="utf-8", errors="replace"), 200, \
        {"Content-Type": "text/plain; charset=utf-8"}


@bp.route("/<task_id>", methods=["GET"])
def get_task(task_id: str):
    """查询单个任务的详细状态。"""
    task = get_scheduler().get_task(task_id)
    if task is None:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(task.to_dict())


@bp.route("/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id: str):
    """取消正在执行的任务（本机 12 位 hex id 或远程 task_* id）。"""
    scheduler = get_scheduler()
    result = scheduler.cancel(task_id)
    if result["success"]:
        return jsonify(result)

    # 本机查无此任务：若是远程任务 ID，同步更新远程索引
    if task_id.startswith("task_"):
        from server.modules.cases import service as cases_service
        records = cases_service.load_remote_tasks()
        target = next((r for r in records if r.get("task_id") == task_id), None)
        if target is not None:
            local_id = target.get("local_task_id")
            stopped_local = False
            if local_id:
                stopped_local = scheduler.cancel(local_id).get("success", False)
            if target.get("status") in ("pending", "running") or stopped_local:
                target["status"] = "stopped"
                target["finished_at"] = target.get("finished_at") or time.time()
                target["error"] = "用户取消"
                cases_service.save_remote_tasks(records[:100])
                return jsonify({"success": True, "message": "任务已停止"})
            return jsonify({"success": False, "message": "任务已结束"}), 400

    return jsonify(result), (200 if result["success"] else 400)


@bp.route("/remote-list", methods=["GET"])
def remote_list():
    """远程任务索引列表（演示版：含历史种子与实时任务）。"""
    from server.modules.cases import service as cases_service
    return jsonify(cases_service.load_remote_tasks())


@bp.route("/remote-remove", methods=["POST"])
def remote_remove():
    """移除远程任务索引记录（机器不可达/状态卡住时使用）。"""
    data = request.get_json(force=True, silent=True) or {}
    task_id = data.get("task_id", "")
    if not task_id:
        return jsonify({"error": "task_id 必填"}), 400
    from server.modules.cases import service as cases_service
    ok = cases_service.remove_remote_record(task_id)
    return jsonify({"success": ok, "error": None if ok else "记录不存在"})


# ---------------------------------------------------------------- 远程任务状态/日志（monitor 页轮询）

@bp.route("/submit", methods=["POST"])
def submit():
    """提交任务。Body: {target_machine, platform, cases, plan, name, skip_install, keep_alive}"""
    data = request.get_json(force=True, silent=True) or {}
    target = data.get("target_machine", "")
    cases = data.get("cases") or []
    if not target or not cases:
        return jsonify({"error": "target_machine 与 cases 为必填"}), 400

    from server.modules.cases import service as cases_service
    result = cases_service.submit_remote_task(
        target, cases,
        platform=data.get("platform", ""),
        plan=data.get("plan") or {},
        name=data.get("name", ""),
    )
    return jsonify(result), (200 if result.get("success") else 500)


def _find_remote(task_id: str):
    from server.modules.cases import service as cases_service
    for r in cases_service.load_remote_tasks():
        if r.get("task_id") == task_id:
            return r
    return None


@bp.route("/<task_id>/status", methods=["GET"])
def task_status(task_id: str):
    """任务状态（远程任务 ID：从索引读取；本机 ID：从 scheduler 读取）。"""
    record = _find_remote(task_id)
    if record is not None:
        return jsonify({
            "task_id": task_id,
            "name": record.get("name", ""),
            "status": record.get("status", "pending"),
            "platform": record.get("platform", ""),
            "cases": record.get("cases", []),
            "started_at": record.get("started_at"),
            "finished_at": record.get("finished_at"),
            "progress": record.get("progress", 0),
            "exit_code": record.get("exit_code"),
            "error": record.get("error"),
        })
    task = get_scheduler().get_task(task_id)
    if task is None:
        return jsonify({"error": "任务不存在"}), 404
    total_steps = max(len(task.steps), 1)
    done = sum(1 for s in task.steps if s.get("status") == "success")
    progress = 100 if task.status.value in ("success", "failed") else min(95, done // total_steps * 90)
    return jsonify({
        "task_id": task_id,
        "name": task.name,
        "status": task.status.value,
        "platform": getattr(task, "platform", ""),
        "cases": getattr(task, "cases", []),
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "progress": progress,
        "exit_code": 0 if task.status.value == "success" else (1 if task.status.value == "failed" else None),
        "error": task.error,
    })


@bp.route("/<task_id>/log", methods=["GET"])
def task_log(task_id: str):
    """任务日志（增量）。Query: offset(默认0), limit(默认200)

    返回 {lines, offset, total, finished}，前端按 offset 增量拉取。
    """
    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 200, type=int)

    content = live_log.read(task_id, tail=10000)
    lines = content.splitlines() if content else []
    total = len(lines)
    chunk = lines[offset:offset + limit]
    finished = False
    record = _find_remote(task_id)
    if record is not None:
        finished = record.get("status") in ("success", "failed", "stopped")
    else:
        task = get_scheduler().get_task(task_id)
        finished = task is not None and task.status.value in ("success", "failed")
    return jsonify({"lines": chunk, "offset": offset + len(chunk),
                    "total": total, "finished": finished})


@bp.route("/<task_id>/result", methods=["GET"])
def task_result(task_id: str):
    """任务结果。远程任务：按 result_file 读历史报告；本机任务：读 task.result。"""
    record = _find_remote(task_id)
    if record is not None:
        if record.get("result_file"):
            f = Path(current_app.config["PROJECT_ROOT"]) / "var" / "results" / "json" / record["result_file"]
            if f.exists():
                import json as _json
                try:
                    return jsonify(_json.loads(f.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    pass
        return jsonify({})
    task = get_scheduler().get_task(task_id)
    if task is None:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(task.result or {})


@bp.route("/<task_id>/video", methods=["GET"])
def task_video(task_id: str):
    """下载录屏（演示：404）。"""
    return jsonify({"error": "演示环境无录屏文件"}), 404
