"""弱网预设配置（演示版）。

通用预设作用于 Mock 服务演示端口；平台预设使用文档保留段（RFC 5737 等）的
虚拟 IP 范围，仅用于演示「按平台采集 IP 段」的覆盖对比，不代表真实运营商网段。
"""
from __future__ import annotations

from .models import ClumsyConfig

MOCK_FILTER = "tcp.DstPort == 8765 or tcp.SrcPort == 8765"


def _range_rule(*bases: str) -> str:
    """把 /16 网段（前两段，如 "192.0"）拼成 WinDivert 双向规则。

    生成的范围 a.b.0.0 - a.b.255.255，与采集器 _preset_ranges 的正则匹配。
    """
    terms = []
    for base in bases:
        lo, hi = f"{base}.0.0", f"{base}.255.255"
        terms.append(f"(ip.DstAddr >= {lo} and ip.DstAddr <= {hi})")
        terms.append(f"(ip.SrcAddr >= {lo} and ip.SrcAddr <= {hi})")
    return " or ".join(terms)


# ── 通用预设（作用于 Mock 服务流量，演示端口 8765）──
PRESETS: dict[str, ClumsyConfig] = {
    "baseline": ClumsyConfig(
        preset_name="基线（无弱网）",
        filter_rule=MOCK_FILTER,
    ),
    "3g": ClumsyConfig(
        preset_name="3G 网络",
        filter_rule=MOCK_FILTER,
        lag_enabled=True,
        lag_time=200,
        drop_enabled=True,
        drop_chance=0.05,
        throttle_enabled=True,
        throttle_chance=0.8,
        throttle_timeframe=100,
    ),
    "2g": ClumsyConfig(
        preset_name="2G 网络（推荐）",
        filter_rule=MOCK_FILTER,
        lag_enabled=True,
        lag_time=500,
        drop_enabled=True,
        drop_chance=0.10,
        throttle_enabled=True,
        throttle_chance=0.9,
        throttle_timeframe=200,
    ),
    "extreme": ClumsyConfig(
        preset_name="极差网络",
        filter_rule=MOCK_FILTER,
        lag_enabled=True,
        lag_time=1000,
        drop_enabled=True,
        drop_chance=0.20,
        throttle_enabled=True,
        throttle_chance=1.0,
        throttle_timeframe=500,
    ),
    "disconnect": ClumsyConfig(
        preset_name="断网模拟",
        filter_rule=MOCK_FILTER,
        drop_enabled=True,
        drop_chance=1.0,
    ),
    # ── 平台预设（虚拟 IP 段，演示采集覆盖对比）──
    "platform_a_2g": ClumsyConfig(
        preset_name="客户端 A · 2G 网络",
        filter_rule=_range_rule("192.0"),
        lag_enabled=True,
        lag_time=500,
        drop_enabled=True,
        drop_chance=0.10,
    ),
    "platform_b_2g": ClumsyConfig(
        preset_name="客户端 B · 2G 网络",
        filter_rule=_range_rule("198.51"),
        lag_enabled=True,
        lag_time=500,
        drop_enabled=True,
        drop_chance=0.10,
    ),
    "platform_c_2g": ClumsyConfig(
        preset_name="网页端 C · 2G 网络",
        filter_rule=_range_rule("203.0"),
        lag_enabled=True,
        lag_time=500,
        drop_enabled=True,
        drop_chance=0.10,
    ),
    "platform_d_2g": ClumsyConfig(
        preset_name="网页端 D · 2G 网络",
        filter_rule=_range_rule("192.0", "198.18"),
        lag_enabled=True,
        lag_time=500,
        drop_enabled=True,
        drop_chance=0.10,
    ),
    # ── 高级测试场景 ──
    "chaos": ClumsyConfig(
        preset_name="混沌网络（多故障叠加）",
        filter_rule=MOCK_FILTER,
        lag_enabled=True,
        lag_time=300,
        drop_enabled=True,
        drop_chance=0.05,
        dup_enabled=True,
        dup_chance=0.03,
        dup_count=2,
        out_of_order_enabled=True,
        out_of_order_chance=0.05,
    ),
}


def get_preset(name: str) -> ClumsyConfig | None:
    """获取预设配置。"""
    return PRESETS.get(name)


def list_presets() -> dict[str, dict]:
    """列出所有预设配置（供前端展示）。"""
    return {
        key: {
            "name": cfg.preset_name,
            "description": _get_preset_description(key),
            "summary": cfg.summary(),
            "config": cfg.to_dict(),
        }
        for key, cfg in PRESETS.items()
    }


def _get_preset_description(key: str) -> str:
    """获取预设配置的详细说明。"""
    descriptions = {
        "baseline": "无弱网注入，用于对比测试基线性能",
        "3g": "延迟 200ms，丢包 5% - 模拟 3G 网络环境，适合轻度弱网测试",
        "2g": "延迟 500ms，丢包 10% - 推荐用于日常弱网测试，模拟 2G 网络环境",
        "extreme": "延迟 1000ms，丢包 20% - 极端弱网场景，测试系统降级能力",
        "disconnect": "100% 丢包 - 模拟完全断网，测试断网后的恢复逻辑",
        "platform_a_2g": "仅影响客户端 A 的虚拟网段流量（192.0.*.*），演示平台级弱网",
        "platform_b_2g": "仅影响客户端 B 的虚拟网段流量（198.51.*.*），演示平台级弱网",
        "platform_c_2g": "仅影响网页端 C 的虚拟网段流量（203.0.*.*），演示平台级弱网",
        "platform_d_2g": "仅影响网页端 D 的虚拟网段流量（192.0.*.* / 198.18.*.*），演示平台级弱网",
        "chaos": "多种故障叠加（延迟+丢包+重复+乱序），测试系统在混沌环境下的健壮性",
    }
    return descriptions.get(key, "")
