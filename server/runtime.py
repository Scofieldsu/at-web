"""运行时上下文 — create_app 时设置项目根路径/当前环境/平台列表。

后台线程（任务调度、定时调度、SSE worker、mock worker）无法依赖
Flask 请求上下文（current_app），统一从本模块读取全局值。
"""
from __future__ import annotations

import threading
from pathlib import Path

_lock = threading.Lock()
_root: Path | None = None
_env: str = "dev"
_platforms: list[dict] = []


def init(root: Path | str, env: str, platforms: list[dict]) -> None:
    """create_app 初始化时调用一次。"""
    global _root, _env, _platforms
    with _lock:
        _root = Path(root)
        _env = env or "dev"
        _platforms = list(platforms or [])


def set_env(env: str) -> None:
    """运行时切换当前环境（/api/env/current 修改 config/env.json 后调用，全局立即生效）。"""
    global _env
    with _lock:
        _env = env or "dev"


def project_root() -> Path:
    if _root is None:
        raise RuntimeError("runtime.init() 未调用")
    return _root


def current_env() -> str:
    return _env


def platforms() -> list[dict]:
    return _platforms


def platform_keys() -> list[str]:
    return [p["key"] for p in _platforms]
