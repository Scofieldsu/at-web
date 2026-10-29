"""故障模拟 · 弹窗模拟：模拟系统级弹窗的弹出与处理（演示版：纯模拟）。

不真正调起模拟器进程、不读真实日志：
- 每次触发生成一条弹出记录与「检测到」日志事件
- 「框被处理」由时间驱动：弹出后约 5-8 秒标记为已关闭，并追加处理日志
- 目标为演示客户端（client-a），不含任何真实 RPA 进程名 / 函数名
"""
from __future__ import annotations

import random
import threading
import time
from datetime import date

from flask import Blueprint, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("fault_popup", __name__, url_prefix="/api/fault/popup")

logger = get_logger(__name__)

EXE_NAME = "popup_sim.exe"
EXE_PATH = "tools/popup/popup_sim.exe"
MODES = {"zh": "线上原文（中文标题）", "std": "系统标准硬错误（标题由系统生成）"}
DEFAULT_CODE = "0xc000012d"
LOG_KEYWORDS = ["检测到系统硬错误框", "系统硬错误框关闭成功", "已清理系统弹窗"]

_lock = threading.RLock()
_rng = random.Random(13)
_pid_seq = _rng.randint(20000, 40000)

# pid -> {mode, code, at, closed_at, closed}
_pids: dict[int, dict] = {}
_history: list[dict] = []
_events: list[dict] = []  # {time, keyword, line}，时间升序


def _log_file() -> str:
    return f"logs/fault-sim-{date.today().isoformat()}.log"


def _now_str() -> str:
    return time.strftime("%H:%M:%S")


def _full_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _add_event(keyword: str, line: str) -> None:
    _events.append({"time": _full_ts(), "keyword": keyword, "line": f"[FaultSim] {line}"})
    if len(_events) > 500:
        del _events[: len(_events) - 500]


def _tick() -> None:
    """时间驱动：到点的模拟框标记为已关闭并追加处理日志。"""
    now = time.time()
    for pid, d in list(_pids.items()):
        if not d["closed"] and now >= d["closed_at"]:
            d["closed"] = True
            for h in _history:
                if h["pid"] == pid:
                    h["alive"] = False
            _add_event(LOG_KEYWORDS[1], f"系统硬错误框关闭成功（PID={pid}，由被测应用处理）")
            _add_event(LOG_KEYWORDS[2], f"已清理 1 个系统弹窗（PID={pid}）")


def _history_row(pid: int, mode: str, code: str | None) -> dict:
    args = [mode] + ([code] if code else [])
    return {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": mode, "args": args,
            "pid": pid, "alive": True}


@bp.route("/status", methods=["GET"])
def status():
    """模拟器就绪状态、未关闭的框、最近弹出记录、当天日志路径。"""
    with _lock:
        _tick()
        return jsonify({
            "exe_exists": True,
            "exe_name": EXE_NAME,
            "exe_path": EXE_PATH,
            "modes": MODES,
            "running": [pid for pid, d in _pids.items() if not d["closed"]],
            "history": list(reversed(_history))[:10],
            "log_file": _log_file(),
        })


@bp.route("/trigger", methods=["POST"])
def trigger():
    """弹出一个模拟系统硬错误框。

    Body:
        {"mode": "zh"}
        {"mode": "std", "code": "0xc000012d"}   # code 省略用默认值
    """
    data = request.get_json(force=True, silent=True) or {}
    mode = str(data.get("mode") or "zh").strip()
    if mode not in MODES:
        return jsonify({"success": False, "message": f"未知模式：{mode or '(空)'}（支持 {'/'.join(MODES)}）"}), 400
    code = str(data.get("code") or "").strip() or (DEFAULT_CODE if mode == "std" else "")

    with _lock:
        global _pid_seq
        _pid_seq += _rng.randint(3, 97)
        pid = _pid_seq
        _pids[pid] = {
            "mode": mode,
            "code": code or None,
            "at": time.time(),
            "closed_at": time.time() + _rng.uniform(5, 8),
            "closed": False,
        }
        _history.insert(0, _history_row(pid, mode, code or None))
        if len(_history) > 30:
            _history.pop()
        _add_event(LOG_KEYWORDS[0], f"检测到系统硬错误框（PID={pid}，由系统弹出，不属于被测进程）")
        logger.info("弹窗模拟触发（演示）: mode=%s code=%s pid=%d", mode, code or "-", pid)
        return jsonify({"success": True, "message": f"已弹出（模拟）：{MODES[mode]}，PID={pid}"})


@bp.route("/events", methods=["GET"])
def events():
    """当天日志里与系统硬错误框相关的行，新的在前。"""
    limit = request.args.get("limit", 200, type=int)
    with _lock:
        _tick()
        rows = list(reversed(_events))
        return jsonify({
            "keywords": LOG_KEYWORDS,
            "log_file": _log_file(),
            "exists": True,
            "events": rows[: max(1, min(limit, 1000))],
        })
