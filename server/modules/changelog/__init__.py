"""版本更新说明 — 展示各平台的版本发布内容（演示数据）。

数据源：config/changelog/<platform>_changelog.json（演示虚构数据）

API:
    GET /api/changelog/platforms          — 有 changelog 的平台列表
    GET /api/changelog/<platform>         — 某平台全部版本（按日期从新到旧）
"""
from flask import Blueprint, jsonify

from .service import get_changelog, get_platforms

bp = Blueprint("changelog", __name__, url_prefix="/api/changelog")


@bp.route("/platforms", methods=["GET"])
def platforms():
    """平台列表（含中文名与版本数量）。"""
    return jsonify({"platforms": get_platforms()})


@bp.route("/<platform>", methods=["GET"])
def changelog(platform: str):
    """某平台的版本更新说明，按日期从新到旧。"""
    return jsonify(get_changelog(platform))
