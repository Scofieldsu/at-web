"""测试计划模块 — 管理各平台的执行参数（版本/安装类型/下载地址/目标机器/店铺/Agent）。

测试计划是「用例执行之前」填写的一份全局配置，保存到 var/data/test_plan.json。
按环境分组（dev/prod），环境由 config/main/config.yaml 的 `current_env` 控制，
切换环境后自动读写对应计划。
"""
from __future__ import annotations

import json

from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("plan", __name__, url_prefix="/api/plan")

# 每个平台的参数模板（空值）
EMPTY_PLATFORM = {
    "version": "",
    "install_type": "main",
    "download_url": "",
    "target_machine": "",
    "shop": "",
    "agent": "",
}

PLAN_RELPATH = "var/data/test_plan.json"


def _platforms() -> list[str]:
    from server import runtime
    return runtime.platform_keys()


def _current_env() -> str:
    """当前环境 — 环境变量 AT_WEB_ENV 覆盖，否则取运行时配置。"""
    import os
    from server import runtime
    return os.getenv("AT_WEB_ENV") or runtime.current_env()


def _plan_path():
    from server import runtime
    return runtime.project_root() / "var" / "data" / "test_plan.json"


def _read_raw() -> dict:
    path = _plan_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _extract_env(data: dict, env: str) -> dict:
    if env in data and isinstance(data[env], dict):
        return data[env]
    if any(p in data for p in _platforms()):
        return data  # 向后兼容旧格式
    return {}


def _default_plan() -> dict:
    return {p: dict(EMPTY_PLATFORM) for p in _platforms()}


@bp.route("/", methods=["GET"])
def get_plan():
    """读取当前环境的测试计划。文件不存在时返回空模板。"""
    env = _current_env()
    path = _plan_path()

    if not path.exists():
        return jsonify({"plan": _default_plan(), "env": env, "path": str(path), "exists": False})

    env_data = _extract_env(_read_raw(), env)
    plan = _default_plan()
    for p in _platforms():
        if isinstance(env_data.get(p), dict):
            plan[p].update({k: v for k, v in env_data[p].items() if k in EMPTY_PLATFORM})

    return jsonify({"plan": plan, "env": env, "path": str(path), "exists": True})


@bp.route("/", methods=["PUT"])
def save_plan():
    """保存当前环境的测试计划（其他环境保持不变）。"""
    env = _current_env()
    data = request.get_json(force=True, silent=True) or {}
    incoming = data.get("plan")
    if not isinstance(incoming, dict):
        return jsonify({"error": "plan 字段必填且为对象"}), 400

    plan = _default_plan()
    for p in _platforms():
        if isinstance(incoming.get(p), dict):
            for k in EMPTY_PLATFORM:
                if k in incoming[p]:
                    plan[p][k] = incoming[p][k]

    path = _plan_path()
    existing = _read_raw()
    if any(p in existing for p in _platforms()):
        all_plans: dict = {env: existing}
    else:
        all_plans = existing
    all_plans[env] = plan

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(all_plans, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        return jsonify({"success": False, "error": f"写入失败: {e}"}), 500
    return jsonify({"success": True, "env": env, "path": str(path)})


@bp.route("/options", methods=["GET"])
def options():
    """返回各平台可选的店铺与 Agent（用于下拉），来自 config/agents/agents.json。

    Returns:
        {"options": {platform: {shop_name: [agent, ...]}}, "env": str}
    """
    env = _current_env()
    from pathlib import Path

    agents_path = Path(current_app.config["PROJECT_ROOT"]) / "config" / "agents" / "agents.json"
    out: dict = {}
    for p in _platforms():
        out[p] = {}
    try:
        data = json.loads(agents_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}

    env_data = data.get("environments", {}).get(env, {})
    for p in _platforms():
        shops = env_data.get(p, {}).get("shops", {})
        out[p] = {shop: list(cfg.get("agents", [])) for shop, cfg in shops.items()}

    return jsonify({"options": out, "env": env})
