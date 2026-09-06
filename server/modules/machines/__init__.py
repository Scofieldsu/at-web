"""机器管理模块 — 分布式执行机集群（演示版：本机 + 演示网段假机器）。

- 机器清单持久化于 var/data/machines.json
- 健康探测为受控演示波动值（10.0.0.11 为本机，其余为演示机）
- 服务更新 = 模拟进度（update-status / update-log 轮询可用）
"""
from __future__ import annotations

import json
import math
import random
import socket
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("machines", __name__, url_prefix="/api/machines")

logger = get_logger(__name__)

DEFAULT_PORT = 5000
LOCAL_LABEL = "本机"

_lock = threading.RLock()  # 可重入：add/remove/label 在持锁时调用 _load/_save
_rng = random.Random(99)

# 演示版本（与 health 模块保持一致）
from server.modules.health import git_version as _git_version, get_remote_main_version

_DEMO_VERSION = _git_version()["version"]


def _machines_file() -> Path:
    return Path(current_app.config["PROJECT_ROOT"]) / "var" / "data" / "machines.json"


def _local_entry() -> dict:
    return {
        "ip": "10.0.0.11",
        "hostname": socket.gethostname(),
        "port": DEFAULT_PORT,
        "label": LOCAL_LABEL,
        "is_local": True,
    }


def _load_machines() -> list[dict]:
    """读取机器清单；缺失/损坏时回退到仅本机。"""
    with _lock:
        f = _machines_file()
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    return data
            except (OSError, json.JSONDecodeError):
                logger.warning("machines.json 读取失败，回退到本机")
        return [_local_entry()]


def _save_machines(machines: list[dict]) -> None:
    with _lock:
        f = _machines_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(machines, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(f)


def _demo_health(ip: str) -> dict:
    """演示健康探测 — 10.0.0.14 固定离线，其余在线且资源波动。"""
    if ip == "10.0.0.14":
        return {"available": False, "status": "offline", "error": "连接超时（演示离线机）"}

    t = time.time() / 60.0
    seed = abs(hash(ip)) % 100
    cpu = 15 + (seed % 20) + 10 * abs(math.sin(t + seed))
    mem = 35 + (seed % 15) + 8 * abs(math.sin(t / 1.7 + seed))
    disk = 40 + (seed % 30)
    return {
        "available": True,
        "status": "online",
        "version": _DEMO_VERSION,
        "git_info": _git_version(),
        "cpu_percent": round(min(cpu, 95), 1),
        "memory_percent": round(min(mem, 90), 1),
        "disk_percent": round(disk, 1),
        "cpu_cores": 8,
        "cpu_model": "Demo CPU (8 cores)",
        "memory_total_gb": 32.0,
        "disk_total_gb": 512.0,
        "services": {"mitmproxy": True, "python_processes": 2, "minio": True},
        "current_task": None,
        "idle": True,
    }


def _probe_all(machines: list[dict]) -> list[dict]:
    out = []
    for m in machines:
        health = _demo_health(m["ip"])
        entry = {**m, **health, "last_check": datetime.now().isoformat(timespec="seconds")}
        out.append(entry)
    return out


@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "machines", "count": len(_load_machines())})


@bp.route("/list", methods=["GET"])
def list_machines():
    """机器列表（含实时健康检查）。"""
    machines = _probe_all(_load_machines())

    online = [m for m in machines if m["available"]]
    versions = sorted({m["version"] for m in online if m.get("version") and m["version"] != "unknown"})

    return jsonify({
        "data": machines,
        "summary": {
            "total": len(machines),
            "online": len(online),
            "idle": len([m for m in machines if m.get("idle")]),
            "versions": versions,
            "version_consistent": len(versions) <= 1,
            "remote_version": get_remote_main_version(),
        },
    })


@bp.route("/add", methods=["POST"])
def add_machine():
    """添加机器。Body: {ip, hostname?, port?, label?}"""
    data = request.get_json(force=True, silent=True) or {}
    ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"error": "ip 为必填参数"}), 400
    port = data.get("port", DEFAULT_PORT)
    try:
        port = int(port)
    except (TypeError, ValueError):
        return jsonify({"error": "port 必须为整数"}), 400

    with _lock:
        machines = _load_machines()
        if any(m["ip"] == ip and m.get("port", DEFAULT_PORT) == port for m in machines):
            return jsonify({"error": f"{ip}:{port} 已在列表中"}), 409
        entry = {
            "ip": ip,
            "hostname": data.get("hostname", ""),
            "port": port,
            "label": data.get("label", ""),
        }
        machines.append(entry)
        _save_machines(machines)

    health = _demo_health(ip)
    logger.info("添加机器: %s:%s status=%s", ip, port, health.get("status"))
    return jsonify({
        "success": True,
        "machine": entry,
        "status": health.get("status"),
        "error": health.get("error"),
    })


@bp.route("/remove", methods=["POST"])
def remove_machine():
    """移除机器。Body: {ip, port?}"""
    data = request.get_json(force=True, silent=True) or {}
    ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"error": "ip 为必填参数"}), 400
    port = data.get("port")
    try:
        port = None if port is None else int(port)
    except (TypeError, ValueError):
        return jsonify({"error": "port 必须为整数"}), 400

    with _lock:
        machines = _load_machines()

        def _matched(m: dict) -> bool:
            return m["ip"] == ip and (port is None or m.get("port", DEFAULT_PORT) == port)

        if any(_matched(m) and m.get("is_local") for m in machines):
            return jsonify({"error": "本机条目不可移除"}), 400

        kept = [m for m in machines if not _matched(m)]
        removed = len(machines) - len(kept)
        if removed:
            _save_machines(kept)

    if not removed:
        return jsonify({"error": f"未找到 {ip}"}), 404
    logger.info("移除机器: %s (%d 条)", ip, removed)
    return jsonify({"success": True, "removed": removed})


@bp.route("/label", methods=["POST"])
def set_label():
    """修改机器标签。Body: {ip, port?, label}"""
    data = request.get_json(force=True, silent=True) or {}
    ip = (data.get("ip") or "").strip()
    port = data.get("port")
    try:
        port = None if port is None else int(port)
    except (TypeError, ValueError):
        return jsonify({"error": "port 必须为整数"}), 400
    if ip is None:
        return jsonify({"error": "ip 为必填参数"}), 400

    updated = 0
    with _lock:
        machines = _load_machines()
        for m in machines:
            if m["ip"] == ip and (port is None or m.get("port", DEFAULT_PORT) == port):
                m["label"] = data.get("label", "")
                updated += 1
        if updated:
            _save_machines(machines)

    if not updated:
        return jsonify({"error": f"未找到 {ip}"}), 404
    return jsonify({"success": True, "updated": updated, "label": data.get("label", "")})


@bp.route("/check", methods=["GET"])
def check_one():
    """探测单台机器。Query: ip, port"""
    ip = request.args.get("ip", "")
    if not ip:
        return jsonify({"error": "ip 为必填参数"}), 400
    return jsonify(_demo_health(ip))


@bp.route("/diff", methods=["GET"])
def get_machine_diff():
    """机器代码差异（演示：与远端一致）。"""
    ip = request.args.get("ip", "")
    if not ip:
        return jsonify({"error": "ip 为必填参数"}), 400
    commit = _git_version()["commit_hash"]
    return jsonify({
        "local_hash": commit,
        "remote_hash": commit,
        "behind": 0,
        "ahead": 0,
        "commits": [],
        "uncommitted_diff": "",
        "untracked_files": [],
        "has_uncommitted": False,
        "truncated": False,
    })


# ---------------------------------------------------------------- 服务更新（模拟）

_updates: dict[str, dict] = {}


@bp.route("/update", methods=["POST"])
def trigger_update():
    """触发服务更新（演示）。Body: {target, port?}"""
    data = request.get_json(force=True, silent=True) or {}
    target = data.get("target", "")
    if not target:
        return jsonify({"error": "target 为必填参数"}), 400

    update_id = f"upd_{int(time.time())}_{target.replace('.', '_')}"

    def _run():
        rec = _updates[update_id]
        rec["status"] = "running"
        lines = _updates[update_id]["_lines"]
        steps = [
            "[下载] 拉取 at-web 包 at-web-1.0.0.tar.gz ... 完成",
            "[校验] SHA256 校验通过",
            "[停止] 停止旧服务 (pid 12345) ... 完成",
            "[部署] 解压到 /opt/at-web ... 完成",
            "[启动] 启动新服务 ... 完成",
            "[验证] 健康检查通过，更新完成",
        ]
        for s in steps:
            time.sleep(0.4)
            lines.append(f"{datetime.now().strftime('%H:%M:%S')} {s}")
        rec["status"] = "success"
        rec["exit_code"] = 0
        rec["finished_at"] = time.time()

    _updates[update_id] = {
        "update_id": update_id,
        "status": "running",
        "exit_code": None,
        "error": "",
        "log_file": f"var/logs/update_{update_id}.log",
        "started_at": time.time(),
        "finished_at": None,
        "_lines": [],
    }
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"success": True, "update_id": update_id,
                    "log_url": f"/api/machines/update-log/{update_id}"})


@bp.route("/update-status/<update_id>", methods=["GET"])
def update_status(update_id: str):
    rec = _updates.get(update_id)
    if rec is None:
        return jsonify({"error": "更新任务不存在"}), 404
    return jsonify({k: v for k, v in rec.items() if not k.startswith("_")})


@bp.route("/update-log/<update_id>", methods=["GET"])
def update_log(update_id: str):
    rec = _updates.get(update_id)
    if rec is None:
        return jsonify({"error": "更新任务不存在"}), 404
    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 200, type=int)
    lines = rec["_lines"]
    chunk = lines[offset:offset + limit]
    return jsonify({
        "lines": chunk,
        "offset": offset + len(chunk),
        "total": len(lines),
        "finished": rec["status"] in ("success", "failed"),
    })
