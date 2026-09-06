"""弱网工具管理 API（演示版）。

端点契约与真实项目一致：
    POST /api/clumsy/start       {"preset": "2g"} 或 {"config": {...}}
    POST /api/clumsy/stop
    GET  /api/clumsy/status
    GET  /api/clumsy/presets
    GET  /api/clumsy/installation
    POST /api/clumsy/validate    {"config": {...}}
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from .models import ClumsyConfig
from .presets import list_presets
from .service import get_service

bp = Blueprint("clumsy", __name__, url_prefix="/api/clumsy")


@bp.route("/start", methods=["POST"])
def start_weaknet():
    """启动弱网（演示）。"""
    service = get_service()
    data = request.get_json(force=True, silent=True) or {}

    if "preset" in data:
        result = service.start(data["preset"])
        return jsonify(result), 200 if result["success"] else 400

    if "config" in data:
        try:
            config = ClumsyConfig.from_dict(data["config"])
            result = service.start(config)
            return jsonify(result), 200 if result["success"] else 400
        except (TypeError, ValueError) as e:
            return jsonify({"success": False, "message": f"配置校验失败：{e}"}), 400

    return jsonify({"success": False, "message": "缺少 preset 或 config 参数"}), 400


@bp.route("/stop", methods=["POST"])
def stop_weaknet():
    """停止弱网（演示）。"""
    result = get_service().stop()
    return jsonify(result), 200 if result["success"] else 400


@bp.route("/status", methods=["GET"])
def get_status():
    """查询运行状态（演示）。"""
    return jsonify(get_service().status().to_dict())


@bp.route("/presets", methods=["GET"])
def get_presets():
    """获取所有预设配置。"""
    return jsonify(list_presets())


@bp.route("/installation", methods=["GET"])
def check_installation():
    """检查安装状态（演示）。"""
    return jsonify(get_service().validate_installation())


@bp.route("/validate", methods=["POST"])
def validate_config():
    """校验配置参数（不启动）。"""
    data = request.get_json(force=True, silent=True) or {}
    if "config" not in data:
        return jsonify({"valid": False, "message": "缺少 config 参数"}), 400

    try:
        config = ClumsyConfig.from_dict(data["config"])
        return jsonify({
            "valid": True,
            "message": "配置校验通过",
            "args": config.to_args(),
            "summary": config.summary(),
        })
    except (TypeError, ValueError) as e:
        return jsonify({"valid": False, "message": f"配置校验失败：{e}"}), 400
