"""弱网预设配置（演示版）。

通用预设作用于 Mock 服务演示端口；平台专属预设作用于各抽象平台的
演示网段（10.0.x.x），与真实项目脱敏一致。
"""
from __future__ import annotations

from .models import ClumsyConfig

# ── 通用预设（作用于 Mock 服务流量，演示端口 8765）──
PRESETS: dict[str, ClumsyConfig] = {
    "baseline": ClumsyConfig(
        preset_name="基线（无弱网）",
        filter_rule="tcp.DstPort == 8765 or tcp.SrcPort == 8765",
    ),
    "3g": ClumsyConfig(
        preset_name="3G 网络",
        filter_rule="tcp.DstPort == 8765 or tcp.SrcPort == 8765",
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
        filter_rule="tcp.DstPort == 8765 or tcp.SrcPort == 8765",
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
        filter_rule="tcp.DstPort == 8765 or tcp.SrcPort == 8765",
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
        filter_rule="tcp.DstPort == 8765 or tcp.SrcPort == 8765",
        drop_enabled=True,
        drop_chance=1.0,
    ),
    # ── 平台A 专用（仅影响平台A 演示网段流量）──
    "platform_a_2g": ClumsyConfig(
        preset_name="平台A 2G 网络",
        filter_rule=(
            "(ip.DstAddr >= 10.0.1.0 and ip.DstAddr <= 10.0.1.255) or "
            "(ip.SrcAddr >= 10.0.1.0 and ip.SrcAddr <= 10.0.1.255)"
        ),
        lag_enabled=True,
        lag_time=500,
        drop_enabled=True,
        drop_chance=0.10,
    ),
    # ── 平台B 专用（仅影响平台B 演示网段流量）──
    "platform_b_2g": ClumsyConfig(
        preset_name="平台B 2G 网络",
        filter_rule=(
            "(ip.DstAddr >= 10.0.2.0 and ip.DstAddr <= 10.0.2.255) or "
            "(ip.SrcAddr >= 10.0.2.0 and ip.SrcAddr <= 10.0.2.255)"
        ),
        lag_enabled=True,
        lag_time=500,
        drop_enabled=True,
        drop_chance=0.10,
    ),
    # ── 高级测试场景 ──
    "chaos": ClumsyConfig(
        preset_name="混沌网络（多故障叠加）",
        filter_rule="tcp.DstPort == 8765 or tcp.SrcPort == 8765",
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
        "platform_a_2g": "仅影响平台A 演示网段流量（10.0.1.*.*），不影响其他服务",
        "platform_b_2g": "仅影响平台B 演示网段流量（10.0.2.*.*），不影响其他服务",
        "chaos": "多种故障叠加（延迟+丢包+重复+乱序），测试系统在混沌环境下的健壮性",
    }
    return descriptions.get(key, "")
