"""故障模拟 · 代理拦截：拦截目标客户端渲染进程的样式（CSS）请求（演示版：纯模拟）。

与源平台 API 契约一致（start/stop/status/hits），但不驱动真实 mitmproxy、不改系统代理：
- 状态 / 命中记录均为内存模拟，命中 URL 为示例 CDN 地址
- 模式：off 仅记录 / 404 一直拦截 / once 只拦前 N 次 / empty 返回空 CSS / delay 延迟放行
- 目标进程、系统代理、外部抓包工具状态均为固定演示值
"""
from __future__ import annotations

import random
import threading
import time

from flask import Blueprint, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("fault_intercept", __name__, url_prefix="/api/fault/intercept")

logger = get_logger(__name__)

MODES = ("off", "404", "once", "empty", "delay")

#: 演示用示例样式 URL（虚拟 CDN 域名）
CSS_URLS = [
    "https://cdn.mock-static.com/app/next.min.css",
    "https://cdn.mock-static.com/app/base.css",
    "https://cdn.mock-static.com/assets/panel.css",
    "https://cdn.mock-static.com/assets/theme-dark.css",
    "https://cdn.mock-static.com/libs/iconfont.css",
]

_lock = threading.RLock()
_rng = random.Random(7)

_state = {
    "running": False,
    "pid": None,
    "started_at": None,
    "control": None,  # {mode, count, delay, path, restart_client}
    "hit_seq": 0,     # once 模式：已拦截次数
}
_hits: list[dict] = []


def _now() -> str:
    return time.strftime("%H:%M:%S")


def _seed_hits() -> None:
    """首次访问预置几条历史记录（演示数据）。"""
    if _hits:
        return
    base = time.time()
    for i, url in enumerate(CSS_URLS[:3]):
        _hits.append({
            "time": time.strftime("%H:%M:%S", time.localtime(base - (i + 1) * 47)),
            "action": "放行（记录）",
            "url": url,
        })


def _pick_url(path: str) -> str:
    if path:
        return f"https://cdn.mock-static.com/app/{path.lstrip('/')}"
    return _rng.choice(CSS_URLS)


def _action_for(control: dict) -> str:
    mode = control["mode"]
    if mode == "off":
        return "放行（记录）"
    if mode == "404":
        return "拦截 404"
    if mode == "once":
        if _state["hit_seq"] < control["count"]:
            _state["hit_seq"] += 1
            return "拦截 404"
        return "放行"
    if mode == "empty":
        return "返回空 CSS（200）"
    if mode == "delay":
        return f"延迟 {control['delay']}s 后放行"
    return "放行（记录）"


def _tick() -> None:
    """运行中每次查询时随机产生 0-2 条命中记录。"""
    if not _state["running"] or _state["control"] is None:
        return
    for _ in range(_rng.randint(0, 2)):
        _hits.append({
            "time": _now(),
            "action": _action_for(_state["control"]),
            "url": _pick_url(_state["control"].get("path", "")),
        })
    if len(_hits) > 500:
        del _hits[: len(_hits) - 500]


@bp.route("/start", methods=["POST"])
def start():
    """开启（或切换）样式拦截。

    Body:
        {"mode": "off|404|once|empty|delay", "count": 1, "delay": 10, "path": "",
         "restart_client": true}
    """
    data = request.get_json(force=True, silent=True) or {}
    try:
        mode = str(data.get("mode", "")).strip()
        count = int(data.get("count", 1))
        delay = int(data.get("delay", 10))
        path = str(data.get("path", "")).strip()
        restart_client = bool(data.get("restart_client", True))
    except (TypeError, ValueError) as e:
        return jsonify({"success": False, "message": f"参数错误: {e}"}), 400
    if mode not in MODES:
        return jsonify({"success": False, "message": f"未知模式：{mode or '(空)'}"}), 400

    with _lock:
        _seed_hits()
        control = {"mode": mode, "count": max(1, count), "delay": max(1, delay),
                   "path": path, "restart_client": restart_client}
        if _state["running"]:
            # 切换模式：保持运行，重置 once 计数
            switched_from = _state["control"]["mode"] if _state["control"] else "-"
            _state["control"] = control
            _state["hit_seq"] = 0
            _hits.append({"time": _now(), "action": f"切换到模式 {mode}（原 {switched_from}）", "url": "-"})
            logger.info("拦截模式切换（演示）: %s -> %s", switched_from, mode)
            return jsonify({"success": True, "message": f"已切换拦截模式：{mode}"})

        _state["running"] = True
        _state["pid"] = _rng.randint(10000, 60000)
        _state["started_at"] = time.time()
        _state["control"] = control
        _state["hit_seq"] = 0
        _hits.append({"time": _now(), "action": "拦截服务已启动（模拟）", "url": "-"})
        if restart_client:
            _hits.append({"time": _now(), "action": "已重启被测客户端并清缓存（模拟）", "url": "-"})
        logger.info("拦截启动（演示）: mode=%s count=%d delay=%d path=%s", mode, count, delay, path)
        return jsonify({"success": True, "message": f"拦截已启动（演示）：模式 {mode}"})


@bp.route("/stop", methods=["POST"])
def stop():
    """停止拦截并撤掉代理绕过项。"""
    with _lock:
        if not _state["running"]:
            return jsonify({"success": False, "message": "拦截未在运行"})
        _state["running"] = False
        _state["pid"] = None
        _state["started_at"] = None
        _state["control"] = None
        _hits.append({"time": _now(), "action": "拦截已停止，绕过项已撤掉（模拟）", "url": "-"})
        logger.info("拦截停止（演示）")
        return jsonify({"success": True, "message": "拦截已停止（演示），系统代理绕过项已恢复"})


@bp.route("/status", methods=["GET"])
def status():
    """拦截状态：模式、PID、被测客户端、系统代理、外部抓包工具、权限。"""
    with _lock:
        _seed_hits()
        _tick()
        running = _state["running"]
        control = dict(_state["control"]) if _state["control"] else None
        bypass_active = running and control is not None and control["mode"] != "off"
        return jsonify({
            "running": running,
            "control": control,
            "pid": _state["pid"] if running else None,
            "target": {
                "install_path": "C:/apps/client-a",
                "version": "9.8.6.214",
                "uses_system_proxy": True,
            },
            "system_proxy": {
                "enabled": True,
                "server": "127.0.0.1:8082",
                "bypass_active": bypass_active,
            },
            "external_capture": {"active": False, "port": 9333},
            "is_admin": True,
        })


@bp.route("/hits", methods=["GET"])
def hits():
    """命中记录，新的在前。"""
    limit = request.args.get("limit", 200, type=int)
    with _lock:
        _seed_hits()
        _tick()
        rows = list(reversed(_hits))
        return jsonify(rows[: max(1, min(limit, 1000))])
