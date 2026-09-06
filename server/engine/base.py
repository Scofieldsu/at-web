"""Engine 接口定义 — 通用测试平台的执行引擎抽象。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class EngineStep:
    """引擎执行中的一个步骤。"""
    name: str          # 步骤名（如 "install_rpa"）
    desc: str = ""     # 展示描述
    duration: float = 0.0  # 建议耗时（秒），由引擎实现决定


class Engine(Protocol):
    """执行引擎协议。

    一次「执行计划」由若干步骤组成，引擎负责：
    - plan_steps():  根据执行目标生成步骤序列（供前端预览进度条）
    - run_step():    执行单步并返回成功与否（引擎内部模拟或真实驱动）

    任务编排（TaskScheduler + TaskRecord）在 tasks 模块，与引擎解耦：
    编排层决定「跑哪些步骤、写哪些日志」，引擎决定「每一步怎么跑」。
    """

    def plan_steps(self, target: dict) -> list[EngineStep]:
        """根据执行目标生成步骤序列。

        Args:
            target: 执行目标描述，至少包含:
                - type: 执行类型（cases/install/online/batch ...）
                - platform: 平台 key
                - cases: 用例列表（type=cases 时）
                - extra: 其他参数
        """
        ...

    def run_step(self, step: EngineStep, ctx: dict) -> dict:
        """执行单个步骤，返回 {"success": bool, "detail": Any}。

        Args:
            step: 要执行的步骤
            ctx: 执行上下文（task_id、platform、cancel_event 等），引擎按需取用
        """
        ...

    def engine_info(self) -> dict:
        """引擎元信息（类型、版本、描述），供 /health 与总览页展示。"""
        ...
