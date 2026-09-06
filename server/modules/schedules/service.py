"""定时任务存储与周期判定（纯逻辑，不依赖 Flask）。

- 数据持久化到 var/data/schedules.json（结构 {"schedules": [...]}）
- spec 支持 4 种周期：daily / weekly / monthly / interval
- next_run_time 计算给定 spec 的下一次运行时间（ISO 字符串）
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from core.logging_config import get_logger

logger = get_logger(__name__)

_DATA_REL = "var/data/schedules.json"


def _file(project_root: str) -> Path:
    return Path(project_root) / _DATA_REL


def load_schedules(project_root: str | None = None) -> list[dict]:
    """读取全部定时任务；文件缺失/损坏返回空列表。"""
    root = project_root or _default_root()
    f = _file(root)
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        items = data.get("schedules") if isinstance(data, dict) else data
        return items if isinstance(items, list) else []
    except (OSError, json.JSONDecodeError):
        logger.warning("schedules.json 解析失败，返回空列表")
        return []


def save_schedules(items: list[dict], project_root: str | None = None) -> None:
    root = project_root or _default_root()
    f = _file(root)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schedules": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


def _default_root() -> str:
    try:
        from server import runtime
        return str(runtime.project_root())
    except Exception:  # noqa: BLE001
        pass
    try:
        from flask import current_app
        return current_app.config["PROJECT_ROOT"]
    except Exception:  # noqa: BLE001
        return str(Path.cwd())


# ---------------------------------------------------------------- spec 校验

def validate_spec(spec: dict) -> str | None:
    """校验 spec，返回错误信息（None 表示通过）。"""
    t = spec.get("type")
    if t not in ("daily", "weekly", "monthly", "interval"):
        return "spec.type 必须是 daily/weekly/monthly/interval"
    if t == "daily":
        return _check_hhmm(spec.get("time"))
    if t == "weekly":
        err = _check_hhmm(spec.get("time"))
        if err:
            return err
        days = spec.get("weekdays")
        if not isinstance(days, list) or not days:
            return "weekly 需要非空 weekdays（isoweekday 1-7）"
        if any(not isinstance(d, int) or not (1 <= d <= 7) for d in days):
            return "weekdays 必须是 1-7 的整数数组"
        return None
    if t == "monthly":
        err = _check_hhmm(spec.get("time"))
        if err:
            return err
        dom = spec.get("day_of_month")
        if not isinstance(dom, int) or not (1 <= dom <= 31):
            return "monthly 需要 day_of_month（1-31）"
        return None
    # interval
    hours = spec.get("interval_hours")
    if not isinstance(hours, (int, float)) or hours < 1:
        return "interval 需要 interval_hours（>=1）"
    return None


def _check_hhmm(value) -> str | None:
    if not isinstance(value, str):
        return "需要 time（HH:MM 格式）"
    parts = value.split(":")
    if len(parts) != 2:
        return "time 格式错误（应为 HH:MM）"
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return "time 格式错误（应为 HH:MM）"
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return "time 超出范围"
    return None


# ---------------------------------------------------------------- 下次运行计算

def next_run_time(spec: dict, after: datetime | None = None) -> str:
    """计算 spec 的下一次运行时间（ISO 字符串）。after 默认 now。"""
    after = after or datetime.now()
    t = spec.get("type")

    if t == "interval":
        hours = float(spec.get("interval_hours", 1))
        return (after + timedelta(hours=hours)).isoformat(timespec="seconds")

    hh, mm = (spec.get("time") or "00:00").split(":")
    hh, mm = int(hh), int(mm)

    if t == "daily":
        cand = after.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if cand <= after:
            cand += timedelta(days=1)
        return cand.isoformat(timespec="seconds")

    if t == "weekly":
        days = sorted({d % 7 for d in spec.get("weekdays", [])})  # 归一化 8→1
        for _ in range(8):
            cand = after.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if cand <= after:
                cand += timedelta(days=1)
            if cand.isoweekday() in days:
                return cand.isoformat(timespec="seconds")
            cand += timedelta(days=1)
        # 兜底
        return (after + timedelta(days=7)).isoformat(timespec="seconds")

    if t == "monthly":
        dom = int(spec.get("day_of_month", 1))
        for _ in range(13):
            y, m = after.year, after.month
            for _off in range(_ + 1):
                mm2 = m + _off
                yy2 = y + (mm2 - 1) // 12
                mm2 = (mm2 - 1) % 12 + 1
                # 找该月 dom 号（超长月取月末）
                last_day = 28
                while True:
                    try:
                        datetime(yy2, mm2, last_day + 1)
                        last_day += 1
                    except ValueError:
                        break
                day = min(dom, last_day)
                try:
                    cand = datetime(yy2, mm2, day, hh, mm, 0)
                except ValueError:
                    continue
                if cand > after:
                    return cand.isoformat(timespec="seconds")
                break
        return (after + timedelta(days=31)).isoformat(timespec="seconds")

    raise ValueError(f"未知 spec.type: {t}")


def _now_ts() -> float:
    return time.time()
