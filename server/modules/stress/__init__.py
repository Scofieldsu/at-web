"""压力测试 API（演示版）。

端点契约与真实项目一致：
    GET  /api/stress/presets     预设场景列表
    POST /api/stress/start       {"config": {...}} 或 {"preset": "standard"}
    POST /api/stress/stop        停止当前压测
    GET  /api/stress/status      运行状态 + 最新指标点
    GET  /api/stress/metrics     实时指标序列（?after=N 增量）
    GET  /api/stress/report      最近一次执行的报告
    GET  /api/stress/history     历史执行记录
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from .engine import get_engine, list_presets

bp = Blueprint("stress", __name__, url_prefix="/api/stress")


@bp.route("/presets", methods=["GET"])
def presets():
    return jsonify(list_presets())


@bp.route("/start", methods=["POST"])
def start():
    engine = get_engine()
    data = request.get_json(force=True, silent=True) or {}
    if "preset" in data:
        p = next((x for x in list_presets() if x["key"] == data["preset"]), None)
        if p is None:
            return jsonify({"success": False, "error": f"预设不存在: {data['preset']}"}), 400
        config = p["config"]
    else:
        config = data.get("config") or {}
    result = engine.start(config)
    return jsonify(result), 200 if result["success"] else 409


@bp.route("/stop", methods=["POST"])
def stop():
    result = get_engine().stop()
    return jsonify(result), 200 if result["success"] else 400


@bp.route("/status", methods=["GET"])
def status():
    return jsonify(get_engine().status())


@bp.route("/metrics", methods=["GET"])
def metrics():
    after = request.args.get("after", 0, type=int)
    return jsonify(get_engine().metrics(after))


@bp.route("/report", methods=["GET"])
def report():
    r = get_engine().report()
    if r is None:
        return jsonify({"available": False})
    return jsonify({"available": True, **r})


@bp.route("/history", methods=["GET"])
def history():
    return jsonify(get_engine().history())
