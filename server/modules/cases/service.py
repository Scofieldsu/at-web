"""用例执行业务逻辑 — DemoEngine 驱动 + 结果文件落盘 + 远程任务索引。

从 cases/__init__.py 拆出，供 tasks 模块（submit/status/log 路由）与
schedules 模块（定时触发）复用，避免包级循环导入。
"""
from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import current_app

from core.logging_config import get_logger
from server import live_log
from server.engine import get_engine
from server.models import TaskStatus

logger = get_logger(__name__)

_rng = random.Random()

# 远程任务索引读改写串行化（可重入）：多线程提交/完成回写时防止丢更新
_remote_lock = threading.RLock()


# ---------------------------------------------------------------- 用例目录

def catalog() -> dict:
    """读取 config/cases.json 用例目录。"""
    from server import runtime
    path = runtime.project_root() / "config" / "cases.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def all_cases() -> list[dict]:
    """展平所有平台的用例条目（含 platform/directory 字段）。"""
    out = []
    for platform, cases in catalog().items():
        for c in cases:
            out.append({
                **c,
                "path": c["file"],
                "platform": platform,
                "directory": f"cases/{platform}",
            })
    return out


# ---------------------------------------------------------------- 结果构造

def build_report(platform: str, cases: list[dict], version: str, task_id: str = "") -> dict:
    """构造 pytest-json-report 结构的演示结果。"""
    tests = []
    for c in cases:
        duration = round(_rng.uniform(0.5, 12.0), 3)
        r = _rng.random()
        outcome = "passed" if r > 0.15 else ("failed" if r > 0.06 else "skipped")
        tests.append({
            "nodeid": f"{c['path']}::{c['name']}",
            "case_name": c["name"],
            "module": c.get("module", ""),
            "outcome": outcome,
            "duration": duration,
            "skipped": None if outcome != "skipped" else "条件不满足（演示）",
            "traceback": "" if outcome == "passed" else (
                "AssertionError: 演示失败（模拟断言错误）\n"
                f"  at {c['path']}:42 in {c['name']}"
            ),
        })
    summary = {
        "total": len(tests),
        "passed": sum(1 for t in tests if t["outcome"] == "passed"),
        "failed": sum(1 for t in tests if t["outcome"] == "failed"),
        "skipped": sum(1 for t in tests if t["outcome"] == "skipped"),
    }
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"batch_{platform}_{ts}.json"
    return {
        "task_name": f"batch:{platform}",
        "task_id": task_id,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration": round(sum(t["duration"] for t in tests) + _rng.uniform(2, 8), 2),
        "platform": platform,
        "version": version,
        "summary": summary,
        "tests": tests,
        "result_file": filename,
        "log_file": filename.replace(".json", ".log"),
    }


def _write_result_files(root: Path, result: dict) -> None:
    """结果 + 日志落盘到 var/results/{json,logs}（测试报告页消费）。"""
    json_dir = root / "var" / "results" / "json"
    log_dir = root / "var" / "results" / "logs"
    json_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    (json_dir / result["result_file"]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"{result['created']} [INFO] 开始批量执行 {result['platform']}（{result['summary']['total']} 条用例）"]
    for t in result["tests"]:
        icon = "[OK]" if t["outcome"] == "passed" else ("[!]" if t["outcome"] == "failed" else "[SKIP]")
        lines.append(f"{result['created']} {icon} {t['case_name']} ({t['duration']}s)")
    s = result["summary"]
    lines.append(f"{result['created']} [结果] 通过 {s['passed']} / 失败 {s['failed']} / 跳过 {s['skipped']}")
    (log_dir / result["log_file"]).write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- 执行核心

def run_cases_task(task, platform: str, targets: list[str]) -> None:
    """任务执行函数：按 DemoEngine 计划走步骤，写实时日志，产出报告。

    task 上需带有 cancel_event 属性（TaskScheduler.submit 挂载）。
    """
    engine = get_engine()
    live_log.init(task.id)
    cancel = getattr(task, "cancel_event", None)

    from server.modules.plan import _current_env, _extract_env, _read_raw
    plan_env = _current_env()
    plan = _extract_env(_read_raw(), plan_env).get(platform, {})
    version = plan.get("version", "")

    def _ts() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if targets:
        matched = [c for c in all_cases()
                   if c["platform"] == platform
                   and any(c["path"] == t or t.rstrip("/") in c["path"] for t in targets)]
    else:
        matched = [c for c in all_cases() if c["platform"] == platform]

    live_log.write(task.id, f"{_ts()} [INFO] 开始执行 {platform}（{len(matched)} 条用例）\n")
    live_log.write(task.id, f"{_ts()} [INFO] 环境: {plan_env}  版本: {version or '未配置'}\n")

    steps = engine.plan_steps({"type": "cases", "platform": platform,
                               "cases": [c["name"] for c in matched]})
    result = None
    for step in steps:
        if cancel is not None and cancel.is_set():
            live_log.write(task.id, f"{_ts()} [!] 用户取消\n")
            return
        task.steps.append({"name": step.name, "status": "running", "desc": step.desc})
        live_log.write(task.id, f"{_ts()} [STEP] {step.name}: {step.desc} ...\n")

        step_result = engine.run_step(step, {"task_id": task.id, "platform": platform,
                                             "cancel_event": cancel,
                                             "_allow_fail": step.name == "execute"})

        if step.name == "execute":
            # 无论引擎步骤成败都产出报告（失败运行也需展示每用例结果）
            result = build_report(platform, matched, version, task_id=task.id)
            n = len(matched) or 1
            for i, c in enumerate(matched, 1):
                if cancel is not None and cancel.is_set():
                    return
                ok = not (not step_result["success"] and i == max(1, n // 2))
                icon = "[OK]" if ok else "[!]"
                live_log.write(task.id,
                               f"{_ts()} {icon} {c['name']} ({_rng.uniform(0.5, 8.0):.1f}s)\n")
                time.sleep(0.05)

        if not step_result["success"]:
            task.steps[-1]["status"] = "failed"
            task.steps[-1]["detail"] = step_result["detail"]
            live_log.write(task.id, f"{_ts()} [!] 步骤 {step.name} 失败: {step_result['detail']}\n")
            task.status = TaskStatus.FAILED
            task.error = step_result["detail"]
            if result is not None:
                task.result = result
                try:
                    from server import runtime
                    _write_result_files(runtime.project_root(), result)
                except OSError:
                    logger.exception("结果文件写入失败")
            live_log.cleanup(task.id)
            return
        task.steps[-1]["status"] = "success"
        live_log.write(task.id, f"{_ts()} [STEP] {step.name} 完成\n")

    if result is None:
        result = build_report(platform, matched, version, task_id=task.id)
    task.result = result

    try:
        from server import runtime
        _write_result_files(runtime.project_root(), result)
    except OSError:
        logger.exception("结果文件写入失败")

    s = result["summary"]
    live_log.write(task.id,
                   f"{_ts()} [结果] 通过 {s['passed']} / 失败 {s['failed']} / 跳过 {s['skipped']}（共 {s['total']}）\n")
    live_log.write(task.id, f"{_ts()} [INFO] 结果文件: {result['result_file']}\n")

    if s["failed"] > 0:
        task.status = TaskStatus.FAILED
        task.error = f"{s['failed']} 条用例失败（演示）"
    # 成功则保持 RUNNING，由调度器置 SUCCESS
    live_log.cleanup(task.id)


# ---------------------------------------------------------------- 远程任务索引（演示单机：远程=本机）

def remote_tasks_file() -> Path:
    from server import runtime
    return runtime.project_root() / "var" / "data" / "remote_tasks.json"


def load_remote_tasks() -> list[dict]:
    with _remote_lock:
        f = remote_tasks_file()
        if not f.exists():
            return []
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []


def save_remote_tasks(records: list[dict]) -> None:
    with _remote_lock:
        f = remote_tasks_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def remove_remote_record(task_id: str) -> bool:
    records = load_remote_tasks()
    kept = [r for r in records if r.get("task_id") != task_id]
    if len(kept) == len(records):
        return False
    save_remote_tasks(kept)
    return True


def submit_remote_task(target_machine: str, cases: list[str], platform: str = "",
                       plan: dict | None = None, name: str = "") -> dict:
    """提交"远程"任务 — 演示版：目标机即本机，本地执行并同步远程索引。"""
    # 延迟导入，避免 tasks 包初始化期的循环导入
    from server.modules.tasks.service import get_scheduler

    now = int(time.time())
    task_id = f"task_{now}_{target_machine.replace('.', '_')}"

    record = {
        "task_id": task_id,
        "target_machine": target_machine,
        "platform": platform,
        "cases": cases,
        "plan": plan or {},
        "name": name or f"远程:{platform or 'mixed'}",
        "created_at": now,
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "progress": 0,
        "exit_code": None,
        "error": None,
        "result_file": None,
        "local_task_id": None,
    }
    # 读改写整体持锁，防止并发提交丢更新
    with _remote_lock:
        records = load_remote_tasks()
        records.insert(0, record)
        save_remote_tasks(records[:100])

    def _commit() -> None:
        """回写远程索引（按 task_id 定位，避免并发覆盖其他任务）。"""
        with _remote_lock:
            all_recs = load_remote_tasks()
            idx = next((i for i, r in enumerate(all_recs) if r.get("task_id") == task_id), None)
            if idx is None:
                all_recs.insert(0, dict(record))
            else:
                all_recs[idx] = dict(record)
            save_remote_tasks(all_recs[:100])

    def run(_task):
        record["local_task_id"] = _task.id
        record["status"] = "running"
        record["started_at"] = time.time()
        _commit()

        live_log.init(task_id)

        def _ts() -> str:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        live_log.write(task_id, f"[远程任务 → {target_machine}] 开始执行 {len(cases)} 个用例目标\n")

        cancel = getattr(_task, "cancel_event", None)
        engine = get_engine()

        from server.modules.plan import _current_env, _extract_env, _read_raw
        plan_env = _current_env()
        plan_data = _extract_env(_read_raw(), plan_env).get(platform, {})
        version = (plan or {}).get("version") or plan_data.get("version", "")

        matched = [c for c in all_cases()
                   if (not platform or c["platform"] == platform)
                   and any(c["path"] == t or t.rstrip("/") in c["path"] for t in cases)]
        if not matched and platform:
            matched = [c for c in all_cases() if c["platform"] == platform]

        steps = engine.plan_steps({"type": "cases", "platform": platform or "mixed",
                                   "cases": [c["name"] for c in matched]})
        live_log.write(task_id, f"{_ts()} [INFO] 环境: {plan_env}  版本: {version or '未配置'}  用例: {len(matched)}\n")

        result = None
        failed = False
        for idx, step in enumerate(steps):
            if cancel is not None and cancel.is_set():
                live_log.write(task_id, f"{_ts()} [!] 用户取消\n")
                break
            live_log.write(task_id, f"{_ts()} [STEP] {step.name}: {step.desc} ...\n")
            step_result = engine.run_step(step, {"task_id": task_id, "platform": platform,
                                                 "cancel_event": cancel,
                                                 "_allow_fail": step.name == "execute"})
            if step.name == "execute":
                # 无论引擎步骤成败都产出报告（失败运行也需展示每用例结果）
                result = build_report(platform or "mixed", matched, version, task_id=task_id)
                for c in matched:
                    if cancel is not None and cancel.is_set():
                        break
                    live_log.write(task_id, f"{_ts()} [OK] {c['name']} ({_rng.uniform(0.5, 8.0):.1f}s)\n")
                    time.sleep(0.05)
            if not step_result["success"]:
                record["error"] = step_result["detail"]
                live_log.write(task_id, f"{_ts()} [!] 步骤 {step.name} 失败: {step_result['detail']}\n")
                failed = True
                break
            live_log.write(task_id, f"{_ts()} [STEP] {step.name} 完成\n")
            record["progress"] = min(95, int((idx + 1) / len(steps) * 90))
            _commit()

        if result is None and not failed:
            result = build_report(platform or "mixed", matched, version, task_id=task_id)

        cancelled = cancel is not None and cancel.is_set()
        has_fail = failed or (isinstance(result, dict) and result["summary"]["failed"] > 0)
        if cancelled:
            record["status"] = "stopped"
            record["exit_code"] = 1
            record["error"] = "用户取消"
        elif has_fail:
            record["status"] = "failed"
            record["exit_code"] = 1
            if not record["error"] and isinstance(result, dict):
                record["error"] = f"{result['summary']['failed']} 条用例失败（演示）"
        else:
            record["status"] = "success"
            record["exit_code"] = 0
            record["error"] = None
        record["finished_at"] = time.time()
        record["progress"] = 100
        if isinstance(result, dict):
            record["result_file"] = result.get("result_file")
            try:
                from server import runtime
                _write_result_files(runtime.project_root(), result)
            except OSError:
                logger.exception("结果文件写入失败")
        _commit()
        live_log.write(task_id, f"[远程任务 → {target_machine}] 执行结束: {record['status']}\n")

    scheduler = get_scheduler()
    local_task = scheduler.submit(record["name"], run, platform=platform, cases=cases)
    record["local_task_id"] = local_task.id
    save_remote_tasks(records[:100])
    return {"success": True, "task_id": task_id, "target_machine": target_machine}
