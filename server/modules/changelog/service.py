"""版本更新说明 — 读取 config/changelog/<platform>_changelog.json。

JSON 结构（key 为版本号，无序）：
    {"2.1.1": {"date": "2026.09", "content": "1、xxx\n\n2、yyy"}}

date 有两种粒度：精确到月（2026.09）或精确到日（2026.08.26），
排序时按 (年, 月, 日) 元组比较，缺日的按当月 0 日处理 —— 同月内
带具体日期的版本排在只写到月的之后，避免月度汇总盖住当月明细。
"""
from __future__ import annotations

import json
from pathlib import Path

# 平台标识 → changelog 文件名。新增平台只改这里。
PLATFORM_FILES = {
    "platform_a": "platform_a_changelog.json",
    "platform_b": "platform_b_changelog.json",
    "platform_c": "platform_c_changelog.json",
    "platform_d": "platform_d_changelog.json",
}

# 平台标识 → 中文名（前端下拉展示用）
PLATFORM_LABELS = {
    "platform_a": "平台A",
    "platform_b": "平台B",
    "platform_c": "平台C",
    "platform_d": "平台D",
}


def _changelog_dir() -> Path:
    from server.runtime import project_root

    return project_root() / "config" / "changelog"


def _parse_date(date_str: str) -> tuple[int, int, int]:
    """把 "2026.09" / "2026.08.26" 解析成可比较的 (年, 月, 日)。

    解析不出来时返回 (0, 0, 0) —— 排到最后，不让脏数据顶到最前面。
    """
    parts = (date_str or "").strip().split(".")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 0
        day = int(parts[2]) if len(parts) > 2 else 0
        return (year, month, day)
    except (ValueError, IndexError):
        return (0, 0, 0)


def get_platforms() -> list[dict]:
    """返回有 changelog 文件的平台列表（含中文名与版本数）。"""
    base = _changelog_dir()
    result = []
    for key, filename in PLATFORM_FILES.items():
        path = base / filename
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
            count = len(data) if isinstance(data, dict) else 0
        except (json.JSONDecodeError, OSError):
            count = 0
        result.append({
            "key": key,
            "label": PLATFORM_LABELS.get(key, key),
            "count": count,
        })
    return result


def get_changelog(platform: str) -> dict:
    """读取某平台的全部版本更新说明（按日期从新到旧）。

    Returns:
        {"platform": str, "label": str, "entries": [{version, date, content}]}
        平台不存在或文件缺失时 entries 为空列表，并带 error 说明。
    """
    filename = PLATFORM_FILES.get(platform)
    if not filename:
        return {
            "platform": platform,
            "label": platform,
            "entries": [],
            "error": f"未知平台: {platform}（可选 {'/'.join(PLATFORM_FILES)}）",
        }

    path = _changelog_dir() / filename
    if not path.exists():
        return {
            "platform": platform,
            "label": PLATFORM_LABELS.get(platform, platform),
            "entries": [],
            "error": f"changelog 文件不存在: config/changelog/{filename}",
        }

    try:
        # utf-8-sig：容忍 Windows 编辑器留下的 BOM
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "platform": platform,
            "label": PLATFORM_LABELS.get(platform, platform),
            "entries": [],
            "error": f"JSON 解析失败（第 {e.lineno} 行）: {e.msg}",
        }
    except OSError as e:
        return {
            "platform": platform,
            "label": PLATFORM_LABELS.get(platform, platform),
            "entries": [],
            "error": f"读取失败: {e}",
        }

    if not isinstance(data, dict):
        return {
            "platform": platform,
            "label": PLATFORM_LABELS.get(platform, platform),
            "entries": [],
            "error": "JSON 顶层应为对象（版本号 → {date, content}）",
        }

    entries = []
    for version, info in data.items():
        if not isinstance(info, dict):
            continue
        entries.append({
            "version": version,
            "date": info.get("date", ""),
            "content": info.get("content", ""),
        })

    # 主序按日期倒序；同日期的按版本号字符串倒序，保证顺序稳定可复现
    entries.sort(key=lambda e: (_parse_date(e["date"]), e["version"]), reverse=True)

    return {
        "platform": platform,
        "label": PLATFORM_LABELS.get(platform, platform),
        "entries": entries,
    }
