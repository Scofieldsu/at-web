"""引擎注册 — create_app 初始化时按配置选择引擎实现。"""
from __future__ import annotations

from .base import Engine
from .demo_engine import DemoEngine

_engine: Engine | None = None


def init_engine(engine_config) -> None:
    """按 EngineConfig 初始化全局引擎（仅 demo 一种内置实现）。"""
    global _engine
    kind = getattr(engine_config, "kind", "demo")
    if kind == "demo":
        _engine = DemoEngine(
            task_duration_min=engine_config.task_duration_min,
            task_duration_max=engine_config.task_duration_max,
            fail_rate=engine_config.fail_rate,
        )
    else:
        # 接入真实引擎的扩展点：按 kind 分发到自定义实现
        raise ValueError(f"未知的引擎类型: {kind}")


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("引擎未初始化，请先调用 init_engine()")
    return _engine
