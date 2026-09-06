"""代理管理模块 — 演示版：模拟代理进程状态 + 拦截规则 CRUD（JSON 持久化）。

源平台此模块驱动真实 mitmproxy；通用框架版保留相同 API 契约：
- 状态为受控模拟（running + 活跃连接数波动）
- 规则 CRUD 持久化到 var/data/proxy_rules.json（seed 预置 4 条）
- start/stop/restart 为同步模拟
"""
from __future__ import annotations

import json
import random
import threading
import time
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("proxy", __name__, url_prefix="/api/proxy")

logger = get_logger(__name__)

_lock = threading.RLock()  # 可重入：规则 CRUD 在持锁时调用 _load/_save
_rng = random.Random(11)


def _rules_file() -> Path:
    return Path(current_app.config["PROJECT_ROOT"]) / "var" / "data" / "proxy_rules.json"


# 代理模拟状态
_state: dict = {
    "running": True,
    "managed": True,
    "url": "http://127.0.0.1:8899",
    "pid": 12345,
    "started_at": time.time() - 3600 * 2,
    "flows": [
        {"flow_id": 24496597620001, "url": "wss://ws-demo.example.com/v1/ws/client?channel=platform_a"},
        {"flow_id": 24496597620002, "url": "wss://ws-demo.example.com/v1/ws/client?channel=platform_b"},
    ],
}


def _load_rules() -> list[dict]:
    f = _rules_file()
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_rules(rules: list[dict]) -> None:
    f = _rules_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "proxy", "running": _state["running"]})


@bp.route("/status", methods=["GET"])
def status():
    """代理运行状态。"""
    with _lock:
        # 演示：连接数小幅波动
        if _state["running"]:
            if _rng.random() < 0.2:
                delta = _rng.choice([-1, 1])
                _state["flows"] = _state["flows"][:max(1, len(_state["flows"]) + delta)]
        return jsonify({
            "running": _state["running"],
            "managed": _state["managed"],
            "url": _state["url"],
            "rules_count": len([r for r in _load_rules() if r.get("enabled", True)]),
            "pid": _state["pid"] if _state["running"] else None,
            "flows": len(_state["flows"]) if _state["running"] else 0,
        })


@bp.route("/start", methods=["POST"])
def start():
    """启动代理（演示）。"""
    data = request.get_json(force=True, silent=True) or {}
    with _lock:
        if _state["running"]:
            return jsonify({"success": True, "message": "代理已在运行", "status": _state})
        time.sleep(0.5)
        _state["running"] = True
        _state["pid"] = _rng.randint(10000, 60000)
        _state["started_at"] = time.time()
        logger.info("代理启动（演示），set_system_proxy=%s", data.get("set_system_proxy", True))
        return jsonify({"success": True, "message": "代理已启动（演示）"})


@bp.route("/stop", methods=["POST"])
def stop():
    """停止代理（演示）。"""
    with _lock:
        if not _state["running"]:
            return jsonify({"success": True, "message": "代理未在运行"})
        _state["running"] = False
        _state["pid"] = None
        _state["flows"] = []
        logger.info("代理停止（演示）")
        return jsonify({"success": True, "message": "代理已停止（演示），系统代理已恢复"})


@bp.route("/restart", methods=["POST"])
def restart():
    """重启代理（演示）。"""
    stop()
    return start()


@bp.route("/flows", methods=["GET"])
def flows():
    """当前活跃的 WebSocket 连接列表。"""
    with _lock:
        if not _state["running"]:
            return jsonify([])
        return jsonify(_state["flows"])


# ---------------------------------------------------------------- 规则 CRUD

@bp.route("/rules", methods=["GET"])
def list_rules():
    """获取当前已安装的所有规则。"""
    return jsonify(_load_rules())


@bp.route("/rules", methods=["POST"])
def create_rule():
    """新增一条规则。"""
    rule = request.get_json(force=True, silent=True) or {}
    if not rule:
        return jsonify({"error": "规则内容不能为空"}), 400
    rule.setdefault("id", f"rule_{uuid.uuid4().hex[:10]}")
    rule.setdefault("name", rule.get("id"))
    rule.setdefault("enabled", True)
    with _lock:
        rules = _load_rules()
        rules.append(rule)
        _save_rules(rules)
    return jsonify({"success": True, "rule": rule})


@bp.route("/rules/clear", methods=["POST"])
def clear_all_rules():
    """清空所有规则。"""
    with _lock:
        _save_rules([])
    return jsonify({"success": True, "removed": 0})


@bp.route("/rules/<rule_id>", methods=["PUT"])
def modify_rule(rule_id: str):
    """修改指定规则（按 id 覆盖）。"""
    rule = request.get_json(force=True, silent=True) or {}
    if not rule:
        return jsonify({"error": "规则内容不能为空"}), 400
    with _lock:
        rules = _load_rules()
        for i, r in enumerate(rules):
            if r.get("id") == rule_id:
                merged = {**r, **rule, "id": rule_id}
                rules[i] = merged
                _save_rules(rules)
                return jsonify({"success": True, "rule": merged})
    return jsonify({"error": f"规则 {rule_id} 不存在"}), 404


@bp.route("/rules/<rule_id>", methods=["DELETE"])
def remove_rule(rule_id: str):
    """删除指定规则。"""
    with _lock:
        rules = _load_rules()
        kept = [r for r in rules if r.get("id") != rule_id]
        if len(kept) == len(rules):
            return jsonify({"error": f"规则 {rule_id} 不存在"}), 404
        _save_rules(kept)
    return jsonify({"success": True})
