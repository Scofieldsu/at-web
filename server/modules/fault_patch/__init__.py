"""故障模拟 · 运行时补丁：把场景补丁注入正在运行的被测客户端主进程（演示版：纯模拟）。

与源平台 API 契约一致（scenarios/status/apply/remove/events），但不做真实内存注入：
- 目标进程为演示客户端（client-a），进程名 / 函数名均脱敏
- 场景登记表为通用故障注入场景（数据读取 / 操作恢复 / 阈值状态 / 面板切换）
- apply/remove 为内存状态切换；事件为按场景关键词生成的模拟日志行
"""
from __future__ import annotations

import random
import threading
import time
from datetime import date

from flask import Blueprint, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("fault_patch", __name__, url_prefix="/api/fault/patch")

logger = get_logger(__name__)

RISK_LABELS = {"low": "低", "medium": "中", "high": "高"}

_LIST_KEYS = ("数量不一致", "刷新冷却中", "分组切换", "列表重建", "刷新完成")
_BLOCK_KEYS = ("状态上报", "清扫弹窗", "重启客户端")


def _s(no, key, group, title, risk, desc, params, keywords, available=True):
    return {"no": no, "key": key, "group": group, "title": title, "risk": risk, "desc": desc,
            "params": params, "keywords": list(keywords), "available": available}


#: 通用故障注入场景登记表（脱敏：不含真实平台进程名 / RPA 业务函数名）
SCENARIOS: list[dict] = [
    _s(1, "read_offset", "数据读取", "读取值偏移", "low",
       "把读到的计数值改成「真实值 + extra」，验证不一致时触发的自动刷新与 30 秒冷却",
       {"extra": 3}, _LIST_KEYS),
    _s(2, "read_fail", "数据读取", "读取值失败", "low",
       "读取计数值抛异常。按 0 处理且不更新内部状态，空闲限频关闭，靠全量扫描兜底",
       {}, ("读取计数失败", "空闲", "全量扫描")),
    _s(3, "list_missing", "数据读取", "列表漏行", "low",
       "藏掉顶部 hide 行、刷新后恢复，验证漏掉的条目被正常处理",
       {"hide": 2}, _LIST_KEYS),
    _s(4, "count_mismatch", "数据读取", "计数与行数不一致", "low",
       "计数改成「行数 + extra」，验证不一致触发的刷新与疑似屏外判定",
       {"extra": 3}, _LIST_KEYS),
    _s(5, "toggle_open_fail", "操作与恢复", "开关操作（开）失败", "low",
       "用「读取值偏移」触发重建。开启操作不真正执行，仍上报「重建完成」；关闭仍是真实执行",
       {"extra": 3}, _LIST_KEYS),
    _s(6, "toggle_close_fail", "操作与恢复", "开关操作（关）失败", "medium",
       "开启仍是真实执行。关闭前 fail_times 次不生效（-1 = 一直失败），随后触发清扫弹窗并重启客户端",
       {"extra": 3, "fail_times": 1}, (*_LIST_KEYS, "无法定位列表控件", "获取用户列表")),
    _s(7, "fetch_error", "操作与恢复", "列表拉取异常", "high",
       "拉取列表抛 UIA 异常，验证交互阻断自愈：清扫弹窗 → 重启客户端",
       {}, ("获取用户列表失败", *_BLOCK_KEYS)),
    _s(8, "stale_name", "操作与恢复", "行名陈旧", "low",
       "指定行（target，留空取第一行）始终对不上，验证陈旧行名触发重建、不产生重复会话",
       {"target": ""}, ("行名陈旧", "面板未对上", *_LIST_KEYS)),
    _s(9, "over_limit", "阈值与状态", "当前负载越限", "medium",
       "当前值改成 served（须 ≥ 上限），验证自动挂起；移除补丁后验证恢复在线",
       {"served": 99}, ("达到上限", "自动切换挂起", "自动恢复在线", "切换挂起失败")),
    _s(10, "status_none", "阈值与状态", "状态读不到", "medium",
       "读取状态返回空。健康上报 client_status=offline；不挂起、不刷新、不重启",
       {}, ("client_status", "客户状态")),
    _s(11, "panel_mismatch", "面板与切换", "面板未对上", "high",
       "所有面板都未对上。仅 1 个已知会话时，动作与「行名陈旧」相同，触发一次分组切换；"
       "重启需持续约 600 秒且涉及至少 3 个不同对象",
       {}, ("面板卡死自愈", "面板未就绪", "未对上", "行名陈旧", "重启客户端"), available=False),
    _s(12, "switch_no_effect", "面板与切换", "切换未生效", "medium",
       "每 every 次点击吞掉 1 次，调用方仍当作已切换，面板停在上一个对象。"
       "验证不串台、不发错对象：主遍历跳过本轮，任务丢弃抓取并重试",
       {"every": 3}, ("吞掉切换点击", "串台", "未跟切", "整批丢弃", "另一行", "未对上")),
    _s(13, "task_switch_no_effect", "面板与切换", "任务切换未生效", "high",
       "只吞任务触发的切换点击（每 every 次吞 1 次），主遍历照常。面板停在上一个对象，"
       "验证任务先等最多 2 秒面板对上，等不到整批丢弃并重试，不发错对象",
       {"every": 1}, ("吞掉任务切换点击", "执行前面板串台", "等待面板后重抓", "丢弃本轮抓取并重试", "任务重试")),
    _s(14, "title_ahead", "面板与切换", "标题领先列表", "medium",
       "每 every 次点击吞掉 1 次，标题读数已更新但列表仍是上一个对象。"
       "验证有对象昵称时不只凭标题判定；抓到的昵称是列表里另一行时整批丢弃",
       {"every": 2}, ("标题领先", "吞掉切换点击", "串台", "另一行", "整批丢弃", "未对上", "丢弃本轮抓取")),
]

_lock = threading.RLock()
_rng = random.Random(23)
_target_pid = _rng.randint(20000, 40000)
_daemon_pid = _rng.randint(1000, 5000)
_active: dict | None = None
_status_lines: list[str] = []
_events: dict[str, list[dict]] = {}  # scenario key -> mock 日志行（时间升序）


def _now_str() -> str:
    return time.strftime("%H:%M:%S")


def _full_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _log_file() -> str:
    return f"logs/client-{date.today().isoformat()}.log"


def _scenario(key: str) -> dict | None:
    return next((s for s in SCENARIOS if s["key"] == key), None)


def _seed_events(scenario: dict, pid: int) -> None:
    """按场景关键词生成一组模拟日志行（演示数据，时间倒推）。"""
    if scenario["key"] in _events:
        return
    rng = random.Random(scenario["key"])
    base = time.time()
    kws = scenario["keywords"]
    rows = []
    for i, kw in enumerate(kws):
        ts = base - (len(kws) - i) * 45 - rng.randint(0, 20)
        rows.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
            "keyword": kw,
            "line": f"[FaultPatch] 命中「{kw}」（场景 {scenario['no']}，目标 PID={pid}）",
        })
    _events[scenario["key"]] = rows


def _push_status(line: str) -> None:
    _status_lines.append(f"{_now_str()} {line}")
    if len(_status_lines) > 20:
        _status_lines.pop(0)


@bp.route("/scenarios", methods=["GET"])
def scenarios():
    """场景清单。available=false 时页面显示「未实现」。"""
    rows = []
    for item in SCENARIOS:
        row = dict(item)
        row["risk_label"] = RISK_LABELS.get(item["risk"], item["risk"])
        rows.append(row)
    return jsonify(rows)


@bp.route("/status", methods=["GET"])
def status():
    """目标进程、当前补丁、注入结果尾部、当天日志路径。"""
    with _lock:
        return jsonify({
            "is_admin": True,
            "tool_ready": True,
            "target_name": "client-a",
            "selected_pid": _target_pid,
            "processes": [
                {"pid": _target_pid, "ppid": _daemon_pid, "memory_mb": 356, "role": "主进程"},
                {"pid": _daemon_pid, "ppid": 1380, "memory_mb": 98, "role": "守护进程"},
            ],
            "active": _active,
            "log_file": _log_file(),
            "status_lines": _status_lines[-5:],
        })


@bp.route("/apply", methods=["POST"])
def apply():
    """注入场景补丁（演示：内存状态切换）。

    Body:
        {"key": "read_offset", "params": {"extra": 3}, "pid": null}
        pid 省略时自动选主进程。
    """
    data = request.get_json(force=True, silent=True) or {}
    key = str(data.get("key") or "").strip()
    scenario = _scenario(key)
    if scenario is None:
        return jsonify({"success": False, "message": f"未知场景：{key or '(空)'}"}), 400
    if not scenario["available"]:
        return jsonify({"success": False, "message": "该场景未实现（演示版未提供补丁文件）"}), 400
    params = data.get("params") or {}
    if not isinstance(params, dict):
        return jsonify({"success": False, "message": "params 须为 JSON 对象"}), 400
    pid = data.get("pid") or None
    try:
        pid = int(pid) if pid not in (None, "") else _target_pid
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "pid 须为整数"}), 400

    with _lock:
        global _active
        if _active is not None and _active["key"] != key:
            _push_status(f"先还原当前补丁「{_active['no']}. {_active['title']}」（模拟）")
            logger.info("补丁替换（演示）: %s -> %s", _active["key"], key)
        _active = {
            "key": key,
            "no": scenario["no"],
            "title": scenario["title"],
            "mode": "always",
            "params": {**scenario["params"], **params},
            "pid": pid,
            "injected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"已注入（模拟）：{scenario['no']}. {scenario['title']}",
            "pid_alive": True,
            "stale": False,
        }
        _push_status(f"找到目标进程 PID={pid}（client-a 主进程，演示）")
        _push_status(f"注入完成（模拟）：{scenario['no']}. {scenario['title']}")
        _seed_events(scenario, pid)
        logger.info("补丁注入（演示）: %s params=%s pid=%d", key, params, pid)
        return jsonify({"success": True,
                        "message": f"注入成功（模拟）：{scenario['no']}. {scenario['title']}"})


@bp.route("/remove", methods=["POST"])
def remove():
    """移除当前补丁（演示：还原内存状态）。"""
    data = request.get_json(force=True, silent=True) or {}
    with _lock:
        global _active
        if _active is None:
            return jsonify({"success": False, "message": "当前没有生效的补丁"})
        title = _active["no"] and f"{_active['no']}. {_active['title']}"
        _active = None
        _push_status(f"已还原（模拟）：{title}，进程行为恢复")
        logger.info("补丁移除（演示）")
        return jsonify({"success": True, "message": f"补丁已移除（模拟）：{title}，进程行为恢复"})


@bp.route("/events", methods=["GET"])
def events():
    """当天日志里命中该场景 keywords 的行，新的在前。key 省略时用当前补丁。"""
    key = (request.args.get("key") or "").strip() or None
    limit = request.args.get("limit", 200, type=int)
    with _lock:
        if key is None and _active is not None:
            key = _active["key"]
        scenario = _scenario(key) if key else None
        if scenario is None:
            return jsonify({"keywords": [], "log_file": _log_file(), "exists": False, "events": []})
        rows = list(reversed(_events.get(key, [])))
        return jsonify({
            "keywords": scenario["keywords"],
            "log_file": _log_file(),
            "exists": True,
            "events": rows[: max(1, min(limit, 1000))],
        })
