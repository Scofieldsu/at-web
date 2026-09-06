"""弱网配置模型（dataclass 版，无 pydantic 依赖）。

弱网注入参数映射（演示版：参数语义与真实工具一致，但不实际影响流量）：
    filter_rule          过滤规则，决定哪些流量被影响
    lag                  延迟毫秒
    drop                 丢包概率（0.0-1.0）
    throttle             节流时间窗（毫秒）
    dup / out_of_order   重复包 / 乱序
    tamper               篡改包内容
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

# 演示环境默认过滤规则（Mock 服务演示端口 8765）
DEFAULT_FILTER = "tcp.DstPort == 8765 or tcp.SrcPort == 8765"


@dataclass
class ClumsyConfig:
    """弱网注入配置。"""

    filter_rule: str = DEFAULT_FILTER
    lag_enabled: bool = False
    lag_time: int = 0

    drop_enabled: bool = False
    drop_chance: float = 0.0

    throttle_enabled: bool = False
    throttle_timeframe: int = 0
    throttle_chance: float = 0.0

    dup_enabled: bool = False
    dup_chance: float = 0.0
    dup_count: int = 2

    out_of_order_enabled: bool = False
    out_of_order_chance: float = 0.0

    tamper_enabled: bool = False
    tamper_chance: float = 0.0

    preset_name: str | None = None

    @classmethod
    def from_dict(cls, d: dict | None) -> "ClumsyConfig":
        """从 dict 构造（忽略未知字段），并校验取值范围。"""
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in (d or {}).items() if k in known}
        cfg = cls(**kwargs)
        cfg.validate()
        return cfg

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> None:
        """校验取值范围（越界抛 ValueError）。"""
        rule = (self.filter_rule or "").strip()
        if len(rule) < 3:
            raise ValueError("过滤规则不能为空")
        keywords = ("tcp", "udp", "ip", "icmp", "inbound", "outbound", "true", "loopback")
        if not any(kw in rule.lower() for kw in keywords):
            raise ValueError("过滤规则格式可能有误，需包含 tcp/udp/ip/inbound/outbound 等关键字")

        if not (0 <= self.lag_time <= 10000):
            raise ValueError("延迟需在 0-10000ms 之间")
        if not (0.0 <= self.drop_chance <= 1.0):
            raise ValueError("丢包概率需在 0.0-1.0 之间")
        if not (0 <= self.throttle_timeframe <= 5000):
            raise ValueError("节流时间窗需在 0-5000ms 之间")
        if not (0.0 <= self.throttle_chance <= 1.0):
            raise ValueError("节流触发概率需在 0.0-1.0 之间")
        if not (0.0 <= self.dup_chance <= 1.0):
            raise ValueError("重复概率需在 0.0-1.0 之间")
        if not (2 <= self.dup_count <= 10):
            raise ValueError("重复份数需在 2-10 之间")
        if not (0.0 <= self.out_of_order_chance <= 1.0):
            raise ValueError("乱序概率需在 0.0-1.0 之间")
        if not (0.0 <= self.tamper_chance <= 1.0):
            raise ValueError("篡改概率需在 0.0-1.0 之间")

    def to_args(self) -> list[str]:
        """转换为弱网注入命令行参数（演示：仅用于展示/日志）。"""
        args = ["--filter", self.filter_rule]

        if self.lag_enabled and self.lag_time > 0:
            args += ["--lag", "on", "--lag-time", str(self.lag_time)]
        if self.drop_enabled and self.drop_chance > 0:
            args += ["--drop", "on", "--drop-chance", f"{self.drop_chance:.4f}"]
        if self.throttle_enabled and self.throttle_chance > 0:
            args += ["--throttle", "on", "--throttle-chance", f"{self.throttle_chance:.4f}"]
            if self.throttle_timeframe > 0:
                args += ["--throttle-timeframe", str(self.throttle_timeframe)]
        if self.dup_enabled and self.dup_chance > 0:
            args += ["--duplicate", "on", "--duplicate-chance", f"{self.dup_chance:.4f}",
                     "--duplicate-count", str(self.dup_count)]
        if self.out_of_order_enabled and self.out_of_order_chance > 0:
            args += ["--ood", "on", "--ood-chance", f"{self.out_of_order_chance:.4f}"]
        if self.tamper_enabled and self.tamper_chance > 0:
            args += ["--tamper", "on", "--tamper-chance", f"{self.tamper_chance:.4f}"]

        return args

    def summary(self) -> str:
        """人类可读的一行摘要。"""
        parts = []
        if self.lag_enabled and self.lag_time:
            parts.append(f"延迟 {self.lag_time}ms")
        if self.drop_enabled and self.drop_chance:
            parts.append(f"丢包 {self.drop_chance * 100:.0f}%")
        if self.throttle_enabled and self.throttle_chance:
            parts.append(f"节流 {self.throttle_timeframe}ms/{self.throttle_chance * 100:.0f}%")
        if self.dup_enabled and self.dup_chance:
            parts.append(f"重复 {self.dup_chance * 100:.0f}%")
        if self.out_of_order_enabled and self.out_of_order_chance:
            parts.append(f"乱序 {self.out_of_order_chance * 100:.0f}%")
        if self.tamper_enabled and self.tamper_chance:
            parts.append(f"篡改 {self.tamper_chance * 100:.0f}%")
        return " / ".join(parts) if parts else "无弱网注入"


@dataclass
class ClumsyStatus:
    """弱网运行状态。"""

    running: bool = False
    installed: bool = False
    exe_path: str = ""
    pid: int | None = None
    config: ClumsyConfig | None = None
    start_time: float | None = None
    elapsed_seconds: int = 0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d
