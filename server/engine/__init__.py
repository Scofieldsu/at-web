"""执行引擎层 — 平台核心抽象。

源平台的真实执行引擎（mitmproxy WS 中间人 + 测试版本安装器 + Playwright）
被整体剥离；本包提供 Engine 接口 + 内置 DemoEngine。

接入真实执行引擎：实现 Engine 接口，并在 create_app 中替换
get_engine() 的返回即可，前端与 API 层无需任何改动。
"""
from .base import Engine, EngineStep
from .demo_engine import DemoEngine
from .registry import get_engine, init_engine

__all__ = ["Engine", "EngineStep", "DemoEngine", "get_engine", "init_engine"]
