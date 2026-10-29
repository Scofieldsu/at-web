"""按平台「采集」客户端实际连接的外网 IP 段，生成过滤规则（演示版：纯模拟）。

真实实现会扫描目标进程的连接表；演示版按平台的虚拟 IP 池模拟采样过程：
- 结果结构与真实版一致（filter_rule / networks / excluded / processes / warnings）
- IP 均取自文档保留段 /16 对齐的虚拟网段（192.0.0.0/16、198.51.0.0/16、
  203.0.0.0/16、198.18.0.0/16），不访问真实网络、不读真实进程、不含任何真实平台进程名
- 采样过程按 0.4s 步进模拟，总耗时封顶约 3.2s
"""
from __future__ import annotations

import ipaddress
import random
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass

from .presets import get_preset


@dataclass(frozen=True)
class PlatformSpec:
    key: str
    label: str
    preset: str  # 对应的弱网预设 key，用于对比旧规则覆盖情况
    ip_pool: tuple[str, ...]  # 虚拟 IP 池（/16 文档保留段）
    processes: tuple[str, ...]  # 模拟进程名（通用名，非真实平台进程）
    kind: str  # client=客户端版 / web=网页版
    hint: str


PLATFORMS: dict[str, PlatformSpec] = {
    "client_a": PlatformSpec(
        key="client_a",
        label="客户端 A",
        preset="platform_a_2g",
        ip_pool=("192.0.0.0/16", "203.0.0.0/16"),
        processes=("app-client.exe", "app-render.exe", "app-worker.exe"),
        kind="client",
        hint="采样期间在客户端 A 里切换几个会话，让常用连接都建起来",
    ),
    "client_b": PlatformSpec(
        key="client_b",
        label="客户端 B",
        preset="platform_b_2g",
        ip_pool=("198.51.0.0/16", "203.0.0.0/16"),
        processes=("app-client.exe", "app-render.exe"),
        kind="client",
        hint="采样期间在客户端 B 里切换几个会话",
    ),
    "web_c": PlatformSpec(
        key="web_c",
        label="网页端 C",
        preset="platform_c_2g",
        ip_pool=("203.0.0.0/16", "198.51.0.0/16"),
        processes=("app-browser.exe",),
        kind="web",
        hint="需先启动网页端 C 并登录，采样期间在它的页面里切换几个会话",
    ),
    "web_d": PlatformSpec(
        key="web_d",
        label="网页端 D",
        preset="platform_d_2g",
        ip_pool=("192.0.0.0/16", "198.18.0.0/16"),
        processes=("app-browser.exe",),
        kind="web",
        hint="需先启动网页端 D 并登录，采样期间在它的页面里切换几个会话",
    ),
}

#: 中控服务器（模拟）：其连接不属于被测业务流量，采集时排除
CONTROL_CENTER_IP = "203.0.113.65"
MAX_NETWORKS = 40
STEP_S = 0.4

_lock = threading.Lock()


class CollectError(Exception):
    """采集无法进行（平台不支持、已有采集在跑）。"""


def list_platforms() -> list[dict]:
    return [{"key": k, "label": s.label, "preset": s.preset, "hint": s.hint} for k, s in PLATFORMS.items()]


def _random_ip(pool: tuple[str, ...], rng: random.Random) -> str:
    net = ipaddress.ip_network(rng.choice(pool), strict=False)
    start = int(net.network_address)
    host = rng.randint(1, net.num_addresses - 2)
    return str(ipaddress.ip_address(start + host))


def _preset_ranges(preset_key: str) -> list[tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]]:
    """解析预设过滤规则里写死的 IP 范围，用于标注采到的网段旧规则是否已覆盖。"""
    preset = get_preset(preset_key)
    if preset is None:
        return []
    rule = preset.filter_rule
    ranges = [(ipaddress.ip_address(a), ipaddress.ip_address(b)) for a, b in
              re.findall(r"Addr >= ([\d.]+) and ip\.\w+ <= ([\d.]+)", rule)]
    ranges += [(ipaddress.ip_address(a), ipaddress.ip_address(a)) for a in re.findall(r"Addr == ([\d.]+)", rule)]
    return ranges


def build_filter(networks: list[ipaddress.IPv4Network], exclude_ips: list[str]) -> str:
    """生成双向匹配的 WinDivert 规则；方向交给各模块的下行/上行开关控制。"""
    terms = []
    for net in networks:
        lo, hi = net[0], net[-1]
        if lo == hi:
            terms.append(f"ip.DstAddr == {lo} or ip.SrcAddr == {lo}")
        else:
            terms.append(f"(ip.DstAddr >= {lo} and ip.DstAddr <= {hi}) or (ip.SrcAddr >= {lo} and ip.SrcAddr <= {hi})")
    rule = " or ".join(terms)
    inside = [ip for ip in exclude_ips if any(ipaddress.ip_address(ip) in n for n in networks)]
    if inside:
        rule = f"({rule})" + "".join(f" and ip.DstAddr != {ip} and ip.SrcAddr != {ip}" for ip in inside)
    return rule


def collect(platform: str, seconds: int = 20, prefix_len: int = 16) -> dict:
    """模拟采样 seconds 秒，按 /prefix_len 归并网段，返回规则和明细（演示：总耗时封顶数秒）。"""
    spec = PLATFORMS.get(platform)
    if spec is None:
        raise CollectError(f"不支持的平台：{platform}")
    if prefix_len not in (16, 24, 32):
        raise CollectError("网段掩码只支持 16 / 24 / 32")
    if not _lock.acquire(blocking=False):
        raise CollectError("已有采集在进行，请等它结束")
    try:
        return _collect(spec, seconds, prefix_len)
    finally:
        _lock.release()


def _collect(spec: PlatformSpec, seconds: int, prefix_len: int) -> dict:
    rng = random.Random()
    base_pid = rng.randint(20000, 50000)
    procs = {name: base_pid + i for i, name in enumerate(spec.processes)}

    # 模拟采样：按 0.4s 步进，每步产生若干条外网连接
    steps = max(1, min(seconds, 8))
    per_step = max(2, seconds // 4)
    hits: Counter[str] = Counter()
    seen_procs: dict[str, set[int]] = {}
    for _ in range(steps):
        for _ in range(per_step):
            name = rng.choice(spec.processes)
            seen_procs.setdefault(name, set()).add(procs[name])
            ip = _random_ip(spec.ip_pool, rng)
            if ip == CONTROL_CENTER_IP:
                continue
            hits[ip] += 1
        time.sleep(STEP_S)

    warnings: list[str] = []
    excluded = sorted({CONTROL_CENTER_IP}, key=lambda ip: int(ipaddress.ip_address(ip)))
    if rng.random() < 0.3:
        warnings.append(f"采到 {rng.randint(1, 5)} 次 IPv6 连接，规则只覆盖 IPv4")
    if rng.random() < 0.25:
        warnings.append("有流量经本地代理 app-proxy:8082 转发，这部分真实 IP 采不到；按 IP 段做弱网前先关代理")
    for ip in excluded:
        hits.pop(ip, None)
    if not hits:
        raise CollectError(f"采样 {seconds} 秒没抓到{spec.label}的外网连接，请重试")

    # 按 /prefix_len 归并网段
    grouped: dict[ipaddress.IPv4Network, list[str]] = {}
    for ip in hits:
        grouped.setdefault(ipaddress.ip_network(f"{ip}/{prefix_len}", strict=False), []).append(ip)
    ordered = sorted(grouped, key=lambda n: -sum(hits[ip] for ip in grouped[n]))
    if len(ordered) > MAX_NETWORKS:
        warnings.append(f"采到 {len(ordered)} 个网段，只保留连接次数最多的 {MAX_NETWORKS} 个；可改用更大的网段掩码")
        ordered = ordered[:MAX_NETWORKS]
    networks = sorted(ordered, key=lambda n: int(n.network_address))

    old = _preset_ranges(spec.preset)
    return {
        "platform": spec.key,
        "label": spec.label,
        "seconds": seconds,
        "prefix_len": prefix_len,
        "filter_rule": build_filter(networks, excluded),
        "networks": [
            {
                "cidr": str(n),
                "ips": sorted(grouped[n], key=lambda ip: int(ipaddress.ip_address(ip))),
                "hits": sum(hits[ip] for ip in grouped[n]),
                "covered": all(any(lo <= ipaddress.ip_address(ip) <= hi for lo, hi in old) for ip in grouped[n]),
            }
            for n in networks
        ],
        "ip_count": sum(len(grouped[n]) for n in networks),
        "excluded": excluded,
        "processes": {name: len(pids) for name, pids in sorted(seen_procs.items())},
        "warnings": warnings,
    }
