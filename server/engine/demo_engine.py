"""DemoEngine — 内置演示执行引擎。

按「执行类型」生成一组模拟步骤，run_step 内按建议耗时 sleep
（可被 cancel_event 打断），返回成功/失败（失败概率由引擎配置控制）。
所有输出均为演示数据，不触碰任何真实设备或网络。
"""
from __future__ import annotations

import random
import threading
import time

from core.logging_config import get_logger

from .base import Engine, EngineStep

logger = get_logger(__name__)


# 各执行类型的标准步骤模板（name, desc, 建议耗时范围）
_STEP_TEMPLATES: dict[str, list[tuple[str, str, tuple[float, float]]]] = {
    "cases": [
        ("env_check", "环境检查", (0.4, 1.0)),
        ("agent_online", "Agent 上线", (1.0, 2.5)),
        ("execute", "用例执行", (2.5, 6.0)),
        ("report", "生成测试报告", (0.5, 1.2)),
    ],
    "batch": [
        ("env_check", "环境检查", (0.4, 1.0)),
        ("agent_online", "Agent 上线", (1.0, 2.5)),
        ("execute", "批量用例执行", (3.0, 7.0)),
        ("rerun_failed", "失败重跑", (0.8, 2.0)),
        ("report", "汇总测试报告", (0.5, 1.2)),
    ],
    "install": [
        ("download", "下载安装包", (1.0, 2.5)),
        ("install_rpa", "执行安装", (1.5, 3.5)),
        ("verify", "安装校验", (0.5, 1.0)),
    ],
    "online": [
        ("launch", "启动被测代理", (0.8, 1.8)),
        ("login", "账号登录", (1.2, 2.8)),
        ("online_check", "上线状态检查", (0.5, 1.2)),
    ],
    "default": [
        ("prepare", "准备", (0.5, 1.2)),
        ("execute", "执行", (1.5, 3.5)),
        ("finish", "收尾", (0.4, 0.8)),
    ],
}


class DemoEngine:
    """演示引擎 — 满足 Engine 协议的全部能力，纯内存模拟。"""

    def __init__(self, task_duration_min: float = 3.0,
                 task_duration_max: float = 8.0, fail_rate: float = 0.15):
        self._min = task_duration_min
        self._max = task_duration_max
        self._fail_rate = fail_rate
        self._rng = random.Random()

    def plan_steps(self, target: dict) -> list[EngineStep]:
        etype = target.get("type", "default")
        template = _STEP_TEMPLATES.get(etype, _STEP_TEMPLATES["default"])
        steps = []
        for name, desc, (lo, hi) in template:
            # 用例执行类步骤按用例数量线性拉长
            if name in ("execute",) and target.get("cases"):
                n = len(target["cases"])
                lo, hi = max(lo, n * 0.8), max(hi, min(n * 1.2, 25))
            steps.append(EngineStep(name=name, desc=desc, duration=self._rng.uniform(lo, hi)))
        return steps

    def run_step(self, step: EngineStep, ctx: dict) -> dict:
        """模拟执行一个步骤。

        失败判定：每个任务只有一次「可能失败」机会（execute 类步骤），
        失败概率取引擎配置的 fail_rate，保证 demo 结果稳定可预期。
        """
        cancel_event: threading.Event | None = ctx.get("cancel_event")
        duration = step.duration
        # 分段 sleep，让 cancel 能尽快生效
        end = time.time() + duration
        while time.time() < end:
            if cancel_event is not None and cancel_event.is_set():
                return {"success": False, "detail": "cancelled"}
            time.sleep(min(0.2, end - time.time()))

        if cancel_event is not None and cancel_event.is_set():
            return {"success": False, "detail": "cancelled"}

        if step.name in ("execute", "rerun_failed") and ctx.get("_allow_fail", True) \
                and self._rng.random() < self._fail_rate:
            return {"success": False,
                    "detail": f"步骤 {step.name} 模拟失败（演示失败率 {int(self._fail_rate * 100)}%）"}

        logger.info("[DemoEngine] step done: %s (%.1fs)", step.name, duration)
        return {"success": True, "detail": f"{step.desc} 完成（{duration:.1f}s）"}

    def engine_info(self) -> dict:
        return {
            "kind": "demo",
            "version": "1.0.0",
            "description": "内置演示引擎 — 模拟步骤执行与结果，可替换为真实引擎",
            "fail_rate": self._fail_rate,
        }
