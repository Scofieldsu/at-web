"""定时任务模块 — REST API 与调度启动（演示版：真实 cron 判定 + 本地触发执行）。

规则持久化到 var/data/schedules.json。调度线程每 60 秒巡检一次，
到点即通过 cases.service.submit_remote_task 触发（演示版远程=本机）。
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from core.logging_config import get_logger

from .service import (
    load_schedules,
    save_schedules,
    next_run_time,
    validate_spec,
)

bp = Blueprint("schedules", __name__, url_prefix="/api/schedules")

logger = get_logger(__name__)

_lock = threading.RLock()
_worker: threading.Thread | None = None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _start_scheduler() -> None:
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    _worker = threading.Thread(target=_loop, daemon=True)
    _worker.start()


def _loop():
    while True:
        time.sleep(30)
        try:
            _tick()
        except Exception:  # noqa: BLE001
            logger.exception("调度巡检异常")


def _tick():
    now_dt = datetime.now()
    for sch in load_schedules():
        if not sch.get("enabled"):
            continue
        next_at = sch.get("next_run_at", "")
        if not next_at:
            continue
        try:
            if now_dt >= datetime.fromisoformat(next_at):
                _trigger(sch)
                # 触发后重算下次
                sch["next_run_at"] = next_run_time(sch["spec"], after=now_dt)
                with _lock:
                    _save_one(sch)
                break
        except ValueError:
            continue


def _save_one(sch: dict) -> None:
    """回写单条定时任务（保留列表中其他条目，避免整表覆盖）。"""
    all_s = load_schedules()
    for i, s in enumerate(all_s):
        if s.get("id") == sch.get("id"):
            all_s[i] = sch
            break
    else:
        all_s.append(sch)
    save_schedules(all_s)


def _trigger(sch: dict):
    """触发一次定时任务（演示：走远程任务链路，即本机执行）。"""
    from server.modules.cases import service as cases_service

    logger.info("定时任务触发: %s (%s)", sch.get("name"), sch.get("id"))
    result = cases_service.submit_remote_task(
        target_machine=sch.get("target_machine", "10.0.0.11"),
        cases=sch.get("cases", []),
        platform=sch.get("platform", ""),
        plan=sch.get("plan", {}),
        name=f"[定时]{sch.get('name', sch.get('id'))}",
    )
    sch["last_triggered_at"] = _now()
    sch["last_run"] = {
        "task_id": result.get("task_id", ""),
        "status": "running",
        "at": _now(),
        "error": None,
    }
    with _lock:
        _save_one(sch)


@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "schedules", "count": len(load_schedules())})


@bp.route("", methods=["GET"], strict_slashes=False)
def list_schedules():
    """列表（含实时计算的 next_run_at）。"""
    now_dt = datetime.now()
    out = []
    for sch in load_schedules():
        s = dict(sch)
        if s.get("enabled"):
            try:
                datetime.fromisoformat(s.get("next_run_at", ""))
            except ValueError:
                s["next_run_at"] = next_run_time(s.get("spec", {}), after=now_dt)
        out.append(s)
    return jsonify({"schedules": out})


@bp.route("", methods=["POST"], strict_slashes=False)
def create_schedule():
    """创建。Body: {name, spec, target_machine, platform, cases, plan, enabled}"""
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    spec = data.get("spec") or {}
    if not name:
        return jsonify({"error": "name 必填"}), 400
    err = validate_spec(spec)
    if err:
        return jsonify({"error": err}), 400
    if not data.get("cases"):
        return jsonify({"error": "cases 不能为空"}), 400

    now_dt = datetime.now()
    sch = {
        "id": f"sch_{uuid.uuid4().hex[:8]}",
        "name": name,
        "enabled": bool(data.get("enabled", True)),
        "spec": spec,
        "target_machine": data.get("target_machine", "10.0.0.11"),
        "platform": data.get("platform", ""),
        "cases": data.get("cases", []),
        "plan": data.get("plan") or {},
        "created_at": _now(),
        "next_run_at": next_run_time(spec, after=now_dt) if data.get("enabled", True) else "",
        "last_triggered_at": "",
        "last_run": None,
    }
    with _lock:
        all_s = load_schedules()
        all_s.append(sch)
        save_schedules(all_s)
    return jsonify(sch), 201


@bp.route("/<sch_id>", methods=["GET"])
def get_schedule(sch_id: str):
    for sch in load_schedules():
        if sch["id"] == sch_id:
            return jsonify(sch)
    return jsonify({"error": "不存在"}), 404


@bp.route("/<sch_id>", methods=["PUT"])
def update_schedule(sch_id: str):
    """更新（允许改 spec/enabled/name/cases/plan/target_machine/platform）。"""
    data = request.get_json(force=True, silent=True) or {}
    with _lock:
        all_s = load_schedules()
        target = next((s for s in all_s if s["id"] == sch_id), None)
        if target is None:
            return jsonify({"error": "不存在"}), 404
        for field in ("name", "enabled", "target_machine", "platform", "cases", "plan"):
            if field in data:
                target[field] = data[field]
        if "spec" in data:
            err = validate_spec(data["spec"])
            if err:
                return jsonify({"error": err}), 400
            target["spec"] = data["spec"]
            if target.get("enabled"):
                target["next_run_at"] = next_run_time(target["spec"], after=datetime.now())
        save_schedules(all_s)
    return jsonify(target)


@bp.route("/<sch_id>", methods=["DELETE"])
def delete_schedule(sch_id: str):
    with _lock:
        all_s = load_schedules()
        kept = [s for s in all_s if s["id"] != sch_id]
        if len(kept) == len(all_s):
            return jsonify({"error": "不存在"}), 404
        save_schedules(kept)
    return jsonify({"success": True})


@bp.route("/<sch_id>/run", methods=["POST"])
def run_schedule(sch_id: str):
    """手动触发一次。"""
    sch = next((s for s in load_schedules() if s["id"] == sch_id), None)
    if sch is None:
        return jsonify({"error": "不存在"}), 404
    try:
        _trigger(sch)
        return jsonify({"success": True, "task_id": (sch.get("last_run") or {}).get("task_id")})
    except Exception as e:  # noqa: BLE001
        logger.exception("手动触发失败")
        return jsonify({"success": False, "error": str(e)}), 500


def start():
    """create_app 注册后调用：启动调度线程。"""
    _start_scheduler()
