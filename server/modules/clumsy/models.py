"""弱网配置模型（dataclass 版，无 pydantic 依赖）。

弱网注入参数映射（演示版：参数语义与真实工具一致，但不实际影响流量）。
每个故障模块都有「下行/上行」两个作用方向；两个方向都关闭的模块视为不生效：
    filter_rule            过滤规则，决定哪些流量被影响
    lag                    延迟毫秒
    drop                   丢包概率（0.0-1.0）
    throttle               节流时间窗（毫秒）+ 触发概率
    bandwidth              限带宽 KB/s
    dup                    重复包（概率 + 份数）
    out_of_order           乱序概率
    tamper                 篡改包内容（概率 + 是否重算校验和）
    reset                  对 TCP 连接注入 RST（概率）
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

# 演示环境默认过滤规则（Mock 服务演示端口 8765）
DEFAULT_FILTER = "tcp.DstPort == 8765 or tcp.SrcPort == 8765"


def _pct(chance: float) -> str:
    """0.0-1.0 概率 → 百分数参数（10 表示 10%）。"""
    return f"{chance * 100:.2f}".rstrip("0").rstrip(".")


def _on(flag: bool) -> str:
    return "on" if flag else "off"


@dataclass
class ClumsyConfig:
    """弱网注入配置。"""

    filter_rule: str = DEFAULT_FILTER

    lag_enabled: bool = False
    lag_time: int = 0
    lag_inbound: bool = True
    lag_outbound: bool = True

    drop_enabled: bool = False
    drop_chance: float = 0.0
    drop_inbound: bool = True
    drop_outbound: bool = True

    throttle_enabled: bool = False
    throttle_timeframe: int = 0
    throttle_chance: float = 0.0
    throttle_inbound: bool = True
    throttle_outbound: bool = True

    bandwidth_enabled: bool = False
    bandwidth_limit: int = 0
    bandwidth_inbound: bool = True
    bandwidth_outbound: bool = True

    dup_enabled: bool = False
    dup_chance: float = 0.0
    dup_count: int = 2
    dup_inbound: bool = True
    dup_outbound: bool = True

    out_of_order_enabled: bool = False
    out_of_order_chance: float = 0.0
    out_of_order_inbound: bool = True
    out_of_order_outbound: bool = True

    tamper_enabled: bool = False
    tamper_chance: float = 0.0
    tamper_checksum: bool = True
    tamper_inbound: bool = True
    tamper_outbound: bool = True

    reset_enabled: bool = False
    reset_chance: float = 0.0
    reset_inbound: bool = True
    reset_outbound: bool = True

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
        if not (0 <= self.bandwidth_limit <= 99999):
            raise ValueError("带宽上限需在 0-99999 KB/s 之间")
        if not (0.0 <= self.dup_chance <= 1.0):
            raise ValueError("重复概率需在 0.0-1.0 之间")
        if not (2 <= self.dup_count <= 50):
            raise ValueError("重复份数需在 2-50 之间")
        if not (0.0 <= self.out_of_order_chance <= 1.0):
            raise ValueError("乱序概率需在 0.0-1.0 之间")
        if not (0.0 <= self.tamper_chance <= 1.0):
            raise ValueError("篡改概率需在 0.0-1.0 之间")
        if not (0.0 <= self.reset_chance <= 1.0):
            raise ValueError("RST 概率需在 0.0-1.0 之间")

    def _modules(self) -> list[tuple[str, str, list[str], bool, bool]]:
        """生效的模块：(模块名, 摘要文案, 模块参数, 下行, 上行)。两个方向都关的模块不算生效。"""
        mods: list[tuple[str, str, list[str], bool, bool]] = []
        if self.lag_enabled and self.lag_time > 0:
            mods.append(("lag", f"延迟 {self.lag_time}ms",
                         ["--lag-time", str(self.lag_time)], self.lag_inbound, self.lag_outbound))
        if self.drop_enabled and self.drop_chance > 0:
            mods.append(("drop", f"丢包 {_pct(self.drop_chance)}%",
                         ["--drop-chance", _pct(self.drop_chance)], self.drop_inbound, self.drop_outbound))
        if self.throttle_enabled and self.throttle_chance > 0:
            extra = ["--throttle-chance", _pct(self.throttle_chance)]
            if self.throttle_timeframe > 0:
                extra += ["--throttle-timeframe", str(self.throttle_timeframe)]
            mods.append(("throttle", f"节流 {self.throttle_timeframe}ms/{_pct(self.throttle_chance)}%",
                         extra, self.throttle_inbound, self.throttle_outbound))
        if self.bandwidth_enabled and self.bandwidth_limit > 0:
            mods.append(("bandwidth", f"限速 {self.bandwidth_limit}KB/s",
                         ["--bandwidth-limit", str(self.bandwidth_limit)],
                         self.bandwidth_inbound, self.bandwidth_outbound))
        if self.dup_enabled and self.dup_chance > 0:
            mods.append(("duplicate", f"重复 {_pct(self.dup_chance)}%×{self.dup_count}",
                         ["--duplicate-count", str(self.dup_count), "--duplicate-chance", _pct(self.dup_chance)],
                         self.dup_inbound, self.dup_outbound))
        if self.out_of_order_enabled and self.out_of_order_chance > 0:
            mods.append(("ood", f"乱序 {_pct(self.out_of_order_chance)}%",
                         ["--ood-chance", _pct(self.out_of_order_chance)],
                         self.out_of_order_inbound, self.out_of_order_outbound))
        if self.tamper_enabled and self.tamper_chance > 0:
            mods.append(("tamper", f"篡改 {_pct(self.tamper_chance)}%",
                         ["--tamper-chance", _pct(self.tamper_chance), "--tamper-checksum", _on(self.tamper_checksum)],
                         self.tamper_inbound, self.tamper_outbound))
        if self.reset_enabled and self.reset_chance > 0:
            mods.append(("reset", f"TCP RST {_pct(self.reset_chance)}%",
                         ["--reset-chance", _pct(self.reset_chance)],
                         self.reset_inbound, self.reset_outbound))
        return [m for m in mods if m[3] or m[4]]

    def to_args(self) -> list[str]:
        """转换为弱网注入命令行参数（演示：仅用于展示/日志）。方向始终显式传。"""
        args = ["--filter", self.filter_rule]
        for name, _, extra, inbound, outbound in self._modules():
            args += [f"--{name}", "on", *extra,
                     f"--{name}-inbound", _on(inbound), f"--{name}-outbound", _on(outbound)]
        return args

    def summary(self) -> str:
        """人类可读的一行摘要。只作用单方向的模块标注（下行）/（上行）。"""
        parts = []
        for _, text, _, inbound, outbound in self._modules():
            if inbound != outbound:
                text += "（下行）" if inbound else "（上行）"
            parts.append(text)
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
    config_version: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d
