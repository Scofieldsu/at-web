"""登录鉴权模块 — 配置式账号 + session cookie。

浏览器走登录后的 session。账号通过 config/main/config.yaml 的 web_users 段配置
（列表，支持多个账号；环境变量 AT_WEB_ADMIN_USER/PASS、AT_WEB_USER2/PASS2 可覆盖）。
默认 admin/demo123 + demo/demo123（演示值）。
"""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request, session

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# 兜底账号（config.yaml 未配置时使用）
_DEFAULT_USERS: dict[str, str] = {
    "admin": "demo123",
    "demo": "demo123",
}


def _web_users() -> dict[str, str]:
    """登录账号表 — 环境变量优先，其次 config.yaml 的 web_users 列表，最后兜底。"""
    from flask import current_app

    users: dict[str, str] = {}
    for item in current_app.config.get("WEB_USERS") or []:
        name = (item.get("username") or "").strip()
        pwd = item.get("password") or ""
        if name and pwd:
            users[name] = pwd
    if not users:
        users.update(_DEFAULT_USERS)
    # 环境变量覆盖/追加（部署时不改配置文件用）
    env_admin = os.getenv("AT_WEB_ADMIN_USER")
    env_pass = os.getenv("AT_WEB_ADMIN_PASS")
    if env_admin and env_pass:
        users[env_admin] = env_pass
    env_user2 = os.getenv("AT_WEB_USER2")
    env_pass2 = os.getenv("AT_WEB_PASS2")
    if env_user2 and env_pass2:
        users[env_user2] = env_pass2
    return users


@bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    user = data.get("username", "")
    pwd = data.get("password", "")
    if _web_users().get(user) == pwd:
        session["user"] = user
        return jsonify({"ok": True, "user": user})
    return jsonify({"ok": False, "error": "用户名或密码错误"}), 401


@bp.post("/logout")
def logout():
    session.pop("user", None)
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    user = session.get("user")
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": user})


def is_authenticated() -> bool:
    """session 已登录则通过。"""
    return bool(session.get("user"))
