"""环境管理模块 — 版本列表、测试版本安装、Agent 上线、浏览器用户（演示版）。

源平台此模块驱动真实安装器与浏览器；通用框架版保留相同 API 契约：
- 版本列表来自 config/platforms/platforms.json 的 versions 段
- 安装/上线 = 同步模拟（带进度步骤），不触碰真实设备
- 用户表 = 从 config/accounts/accounts.yaml 读取的演示账号
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import yaml
from flask import Blueprint, current_app, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("env", __name__, url_prefix="/api/env")

logger = get_logger(__name__)

_rng = random.Random(42)

def _platform_type_map() -> dict[str, int]:
    """platform_type 数字编码映射（平台 key → 数字，取自 platforms.json 的 type 字段）。"""
    from server import runtime
    return {p["key"]: (p.get("type") or i) for i, p in enumerate(runtime.platforms(), start=1)}


def _platforms() -> list[str]:
    from server import runtime
    return runtime.platform_keys()


def _platform_cfg() -> dict:
    path = Path(current_app.config["PROJECT_ROOT"]) / "config" / "platforms" / "platforms.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _accounts_cfg() -> dict:
    path = Path(current_app.config["PROJECT_ROOT"]) / "config" / "accounts" / "accounts.yaml"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _agents_cfg() -> dict:
    path = Path(current_app.config["PROJECT_ROOT"]) / "config" / "agents" / "agents.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _current_env() -> str:
    import os
    from server import runtime
    return os.getenv("AT_WEB_ENV") or runtime.current_env()


def _allowed_envs() -> list[str]:
    """可选环境列表 — 来自 config/env.json 的 _可选值，缺省 dev/prod。"""
    from core.config import ENV_JSON_RELPATH
    path = Path(current_app.config["PROJECT_ROOT"]) / ENV_JSON_RELPATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        values = data.get("_可选值")
        if isinstance(values, list) and values:
            return [str(v) for v in values]
    except (OSError, json.JSONDecodeError):
        pass
    return ["dev", "prod"]


# ---------------------------------------------------------------- 当前环境读写（config/env.json）

@bp.route("/current", methods=["GET"])
def get_current_env():
    """当前环境（config/env.json 的 current，可被环境变量 AT_WEB_ENV 覆盖）。"""
    import os
    return jsonify({
        "env": _current_env(),
        "envs": _allowed_envs(),
        "source": "env_var" if os.getenv("AT_WEB_ENV") else "config/env.json",
    })


@bp.route("/current", methods=["PUT"])
def put_current_env():
    """切换当前环境 — 写入 config/env.json 的 current 并立即全局生效。

    Body: {"env": "dev" | "prod"}
    """
    data = request.get_json(force=True, silent=True) or {}
    env = str(data.get("env", "")).strip()
    if env not in _allowed_envs():
        return jsonify({"error": f"无效环境: {env}，可选: {_allowed_envs()}"}), 400

    from core.config import save_current_env
    from server import runtime

    try:
        save_current_env(current_app.config["PROJECT_ROOT"], env)
    except OSError as e:
        return jsonify({"success": False, "error": f"写入 config/env.json 失败: {e}"}), 500
    runtime.set_env(env)
    logger.info("环境已切换: %s", env)
    return jsonify({"success": True, "env": env})


# ---------------------------------------------------------------- 查询类

@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "env", "platforms": _platforms()})


@bp.route("/status", methods=["GET"])
def status():
    """环境就绪状态（演示：全部就绪）。"""
    checks = {name: True for name in ("flask", "yaml", "engine")}
    return jsonify({"ready": all(checks.values()), "checks": checks})


@bp.route("/accounts", methods=["GET"])
def test_accounts():
    """当前环境各平台的测试账号配置（来自 config/agents/agents.json）。"""
    env = _current_env()
    env_data = _agents_cfg().get("environments", {}).get(env, {})
    accounts = {}
    for p in _platforms():
        acc = env_data.get(p)
        if acc:
            accounts[p] = {
                "shop_name": acc.get("shops", {}) and list(acc.get("shops", {}).keys())[0],
                "agent_name": acc.get("default_agent", ""),
                "target_contact": acc.get("target_contact", ""),
            }
    return jsonify({"env": env, "accounts": accounts})


# ---------------------------------------------------------------- 版本与安装

@bp.route("/versions", methods=["GET"])
def list_versions_endpoint():
    """指定平台可用版本列表（来自 platforms.json 的 versions 段，最新在前）。"""
    platform = request.args.get("platform", "")
    if not platform:
        return jsonify({"error": "platform 为必填参数"}), 400
    versions = _platform_cfg().get(platform, {}).get("versions", [])
    if not versions:
        return jsonify({"error": f"不支持的平台: {platform}"}), 400
    return jsonify({"platform": platform, "versions": versions})


def _simulate_install(platform: str, version: str, install_type: str) -> dict:
    """模拟安装流程 — 分步等待，返回结构化结果。"""
    steps = []
    for name in (f"download_{install_type}_package", "install_rpa", "verify_install"):
        elapsed = _rng.uniform(0.3, 1.2)
        time.sleep(elapsed)
        steps.append({"step": name, "success": True, "detail": f"完成（{elapsed:.1f}s）"})
    return {
        "success": True,
        "platform": platform,
        "version": version,
        "install_type": install_type,
        "steps": steps,
        "message": f"{platform} {version} 安装成功（演示）",
    }


@bp.route("/install-rpa", methods=["POST"])
def install_rpa_endpoint():
    """安装测试版本（演示）。Body: {platform, version, install_type, download_url, target_machine}"""
    data = request.get_json(force=True, silent=True) or {}
    platform = data.get("platform", "")
    version = data.get("version", "")
    if not platform or not version:
        return jsonify({"error": "platform 与 version 为必填"}), 400
    if platform not in _platforms():
        return jsonify({"error": f"不支持的平台: {platform}"}), 400
    result = _simulate_install(platform, version, data.get("install_type", "main"))
    logger.info("测试版本安装（演示）: %s %s → %s", platform, version, result["message"])
    return jsonify(result)


@bp.route("/online-agent", methods=["POST"])
def online_agent_endpoint():
    """Agent 上线（演示）。Body: {platform, shop, agent}"""
    data = request.get_json(force=True, silent=True) or {}
    platform = data.get("platform", "")
    shop = data.get("shop", "")
    agent = data.get("agent", "")
    if not (platform and shop and agent):
        return jsonify({"error": "platform、shop、agent 为必填"}), 400

    time.sleep(_rng.uniform(0.5, 1.5))
    logger.info("Agent 上线（演示）: %s %s %s", platform, shop, agent)
    return jsonify({
        "success": True,
        "platform": platform,
        "shop": shop,
        "agent": agent,
        "message": f"{agent} 已上线（演示）",
    })


# ---------------------------------------------------------------- 浏览器用户（演示账号表）

@bp.route("/create-users", methods=["POST"])
def create_users_endpoint():
    """创建浏览器用户（演示）— 从 accounts.yaml 分配演示账号。

    Body: {platform, count, login_mode, start_port?}
    """
    data = request.get_json(force=True, silent=True) or {}
    platform = data.get("platform", "")
    count = int(data.get("count", 1) or 1)
    if platform not in _platforms():
        return jsonify({"error": f"不支持的平台: {platform}"}), 400

    time.sleep(_rng.uniform(0.5, 1.5))
    accounts = (_accounts_cfg().get(platform) or {}).get("accounts", [])
    tmap = _platform_type_map()
    users = []
    for i in range(min(count, max(len(accounts), count))):
        acc = accounts[i % len(accounts)] if accounts else {"port": 7000 + i,
                                                            "username": f"demo_user_{i + 1}"}
        users.append({
            "port": acc.get("port", 7000 + i),
            "username": acc.get("username", f"demo_user_{i + 1}"),
            "platform": platform,
            "platform_type": tmap.get(platform, 0),
            "logged_in": True,
        })
    logger.info("创建浏览器用户（演示）: %s x%d", platform, len(users))
    return jsonify({"success": True, "users": users,
                    "message": f"已创建 {len(users)} 个用户（演示）"})


@bp.route("/users", methods=["GET"])
def list_users():
    """列出各平台演示账号（含在线状态）。Query: platform(可选)"""
    platform_filter = request.args.get("platform", "")
    tmap = _platform_type_map()
    type_filter = tmap.get(platform_filter) if platform_filter else None

    users = []
    for p in _platforms():
        if type_filter and tmap.get(p) != type_filter:
            continue
        for acc in (_accounts_cfg().get(p) or {}).get("accounts", []):
            users.append({
                "port": acc.get("port"),
                "username": acc.get("username", ""),
                "platform_type": tmap.get(p),
                "logged_in": True,  # 演示：全部在线
            })
    return jsonify({"users": users})


@bp.route("/users/rescan", methods=["POST"])
def rescan_users():
    """重新扫描演示账号（演示：返回扫描数量）。"""
    total = sum(len((_accounts_cfg().get(p) or {}).get("accounts", [])) for p in _platforms())
    return jsonify({"success": True, "scanned": total})
