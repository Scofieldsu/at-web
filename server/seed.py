"""假种子数据 — 首次启动时填充演示数据（任务历史、版本记录、规则、计划等）。

所有数据均为虚构的演示值：
- 平台 key: platform_a / platform_b / platform_c（config/platforms/platforms.json 驱动）
- 机器: 10.0.0.11 ~ 10.0.0.16（演示网段）
- 结果: 随机但稳定的通过/失败分布（固定随机种子，重启后数据一致）

填充目标（都在 var/data 与 var/results 下，gitignore）：
    test_plan.json            测试计划（dev/prod 双环境）
    version_records.json      版本测试记录（3 平台 × 4 版本）
    proxy_rules.json          拦截规则（4 条预置）
    schedules.json            定时任务（3 条预置）
    results/json/*.json       历史执行报告（12 份）+ 对应日志
    results/logs/*.log
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

from core.logging_config import get_logger

logger = get_logger(__name__)

_RNG = random.Random(20260905)  # 固定种子，保证重启后演示数据一致

# 每个平台的版本序列（演示版本号）
_PLATFORM_VERSIONS = {
    "platform_a": ["1.4.2", "1.4.1", "1.4.0", "1.3.9"],
    "platform_b": ["2.1.0", "2.0.8", "2.0.7", "2.0.5"],
    "platform_c": ["0.9.6", "0.9.5", "0.9.4", "0.9.2"],
    "platform_d": ["3.2.1", "3.2.0", "3.1.8", "3.1.5"],
}

# 每个平台的用例集（nodeid 风格的演示用例）
_CASES = {
    "platform_a": [
        ("install", "test_install_rpa_smoke"),
        ("install", "test_install_rpa_full"),
        ("online", "test_agent_online"),
        ("online", "test_agent_reconnect"),
        ("message", "test_send_text_reply"),
        ("message", "test_send_image_reply"),
        ("message", "test_send_card_reply"),
        ("transfer", "test_transfer_to_human"),
        ("message", "test_idempotent_reply"),
        ("message", "test_forbidden_word_filter"),
    ],
    "platform_b": [
        ("install", "test_install_rpa_smoke"),
        ("install", "test_install_rpa_full"),
        ("online", "test_agent_online"),
        ("online", "test_agent_reconnect"),
        ("message", "test_send_text_reply"),
        ("message", "test_send_video_reply"),
        ("message", "test_send_order_reply"),
        ("transfer", "test_transfer_to_human"),
        ("message", "test_search_reply"),
        ("message", "test_batch_message"),
    ],
    "platform_c": [
        ("install", "test_install_rpa_smoke"),
        ("online", "test_agent_online"),
        ("message", "test_send_text_reply"),
        ("message", "test_send_image_reply"),
        ("transfer", "test_transfer_to_human"),
        ("message", "test_idempotent_reply"),
    ],
    "platform_d": [
        ("install", "test_install_rpa_smoke"),
        ("install", "test_install_rpa_full"),
        ("online", "test_agent_online"),
        ("message", "test_send_text_reply"),
        ("message", "test_send_card_reply"),
        ("transfer", "test_transfer_to_human"),
        ("message", "test_batch_message"),
    ],
}


def _now_ts() -> float:
    return time.time()


def seed_all(project_root: Path, platforms: list[dict]) -> None:
    """填充全部演示数据。幂等：已有数据则跳过。"""
    data_dir = project_root / "var" / "data"
    results_dir = project_root / "var" / "results"
    data_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    keys = [p["key"] for p in platforms] or ["platform_a"]

    plan_file = data_dir / "test_plan.json"
    if plan_file.exists():
        logger.info("seed 跳过：test_plan.json 已存在")
        return

    logger.info("开始填充演示数据（%s）", ", ".join(keys))

    _seed_cases_config(project_root / "config", keys)
    _seed_test_plan(data_dir, plan_file, platforms)
    _seed_version_records(data_dir, keys)
    _seed_proxy_rules(data_dir)
    _seed_schedules(data_dir)
    _seed_remote_tasks(data_dir)
    _seed_machines(data_dir)
    _seed_results(results_dir, keys)
    logger.info("演示数据填充完成")


# ---------------------------------------------------------------- 用例目录

# 模块 → 演示 mark 映射
_MODULE_MARKS = {
    "install": ["install", "smoke"],
    "online": ["online", "smoke"],
    "message": ["message", "regression"],
    "transfer": ["transfer", "regression"],
}

# 演示 doc 注释（文件头部注释风格）
_CASE_DOCS = {
    "install": "测试版本安装冒烟/全量流程：下载 → 安装 → 进程与窗口校验",
    "online": "Agent 上线：启动被测代理 → 登录 → 上线状态与重连校验",
    "message": "消息收发：文本/图片/卡片/订单回复与幂等、禁词、批量场景",
    "transfer": "转人工：触发条件 → 转接 → 会话交接校验",
}

# 子场景（参数化测试 id）
_CASE_SCENARIOS = {
    "test_install_rpa_smoke": ["main", "quick"],
    "test_install_rpa_full": ["main", "upgrade"],
    "test_agent_online": ["first_login", "relogin"],
    "test_agent_reconnect": ["network_drop", "agent_restart"],
    "test_send_text_reply": ["greeting", "stock", "shipping"],
    "test_send_image_reply": ["product_pic", "detail_pic"],
    "test_send_card_reply": ["item_card", "coupon_card"],
    "test_send_video_reply": ["intro_video"],
    "test_send_order_reply": ["order_query", "order_status"],
    "test_transfer_to_human": ["user_request", "forbidden_word"],
    "test_idempotent_reply": ["duplicate_msg", "reorder_msg"],
    "test_forbidden_word_filter": ["sensitive_text"],
    "test_search_reply": ["keyword_hit", "keyword_miss"],
    "test_batch_message": ["5_users", "20_users"],
}


def _seed_cases_config(config_root: Path, keys: list[str]) -> None:
    """生成 config/cases.json — 演示用例目录（用例树数据源）。"""
    catalog: dict = {}
    for key in keys:
        cases = []
        for module, case_name in _CASES.get(key, []):
            file = f"cases/{key}/{case_name}.py"
            marks = [key] + _MODULE_MARKS.get(module, ["regression"])
            if case_name == "test_batch_message":
                marks.append("stress")
            if case_name == "test_agent_reconnect":
                marks.append("slow")
            cases.append({
                "file": file,
                "name": case_name,
                "module": module,
                "marks": marks,
                "doc": _CASE_DOCS.get(module, ""),
                "scenarios": _CASE_SCENARIOS.get(case_name, []),
            })
        catalog[key] = cases
    (config_root / "cases.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------- 远程任务索引

def _seed_remote_tasks(data_dir: Path) -> None:
    """种子远程任务记录（历史，全部已结束）。"""
    now = _now_ts()
    records = []
    specs = [
        ("10.0.0.11", "platform_a", 2, "success", 1),
        ("10.0.0.12", "platform_b", 1, "success", 2),
        ("10.0.0.13", "platform_c", 1, "failed", 3),
    ]
    for i, (ip, platform, days_ago, status, _n) in enumerate(specs):
        ts = int(now - days_ago * 86400)
        task_id = f"task_{ts}_{ip.replace('.', '_')}"
        cases = [f"cases/{platform}/"]
        finished = ts + 420
        records.append({
            "task_id": task_id,
            "target_machine": ip,
            "platform": platform,
            "cases": cases,
            "plan": {"version": _PLATFORM_VERSIONS.get(platform, ["1.0.0"])[0], "shop": "", "agent": ""},
            "name": f"远程回归:{platform}",
            "created_at": ts,
            "status": status,
            "started_at": ts + 3,
            "finished_at": finished,
            "progress": 100,
            "exit_code": 0 if status == "success" else 1,
            "error": None if status == "success" else "用例 test_send_image_reply 失败（演示）",
            "result_file": f"batch_{platform}_{datetime.fromtimestamp(ts).strftime('%Y%m%d_%H%M%S')}.json",
        })
    path = data_dir / "remote_tasks.json"
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 机器清单

def _seed_machines(data_dir: Path) -> None:
    """机器清单（本机 + 演示网段 10.0.0.11~16）。

    10.0.0.14 为固定离线演示机（机器页"离线"状态展示用）。
    """
    import socket

    machines = [
        {"ip": "10.0.0.11", "hostname": socket.gethostname(), "port": 5000,
         "label": "本机", "is_local": True},
        {"ip": "10.0.0.12", "hostname": "demo-node-02", "port": 5000, "label": "执行机 2"},
        {"ip": "10.0.0.13", "hostname": "demo-node-03", "port": 5000, "label": "执行机 3"},
        {"ip": "10.0.0.14", "hostname": "demo-node-04", "port": 5000, "label": "执行机 4（离线）"},
        {"ip": "10.0.0.15", "hostname": "demo-node-05", "port": 5000, "label": "执行机 5"},
        {"ip": "10.0.0.16", "hostname": "demo-node-06", "port": 5000, "label": "执行机 6"},
    ]
    path = data_dir / "machines.json"
    path.write_text(json.dumps(machines, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 测试计划

def _seed_test_plan(data_dir: Path, plan_file: Path, platforms: list[dict]) -> None:
    """dev/prod 双环境计划，dev 填完整参数，prod 部分留空。"""
    plan = {"dev": {}, "prod": {}}
    for p in platforms:
        key = p["key"]
        dev = {
            "version": _PLATFORM_VERSIONS.get(key, ["1.0.0"])[0],
            "install_type": "main",
            "download_url": f"http://10.0.0.100/packages/{key}/agent-{_PLATFORM_VERSIONS.get(key, ['1.0.0'])[0]}.zip",
            "target_machine": "10.0.0.11",
            "shop": f"演示店铺{p.get('name', key).replace('平台', '')}",
            "agent": f"agent_{key.split('_')[-1]}_01",
        }
        prod = {
            "version": _PLATFORM_VERSIONS.get(key, ["1.0.0"])[1] if len(_PLATFORM_VERSIONS.get(key, [])) > 1 else "",
            "install_type": "full",
            "download_url": "",
            "target_machine": "10.0.0.13",
            "shop": f"演示店铺{p.get('name', key).replace('平台', '')}",
            "agent": f"agent_{key.split('_')[-1]}_02",
        }
        plan["dev"][key] = dev
        plan["prod"][key] = prod
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 版本记录

def _seed_version_records(data_dir: Path, keys: list[str]) -> None:
    """3 平台 × 4 版本的用例通过状态矩阵。新版本通过率整体更高（演示趋势）。"""
    records: dict = {}
    for key in keys:
        records[key] = {}
        for v_idx, version in enumerate(_PLATFORM_VERSIONS.get(key, [])):
            now = _now_ts()
            cases = {}
            for module, case_name in _CASES.get(key, []):
                # 旧版本（v_idx 大）失败更多
                fail_bias = 0.10 + v_idx * 0.08
                passed = _RNG.random() > fail_bias
                report = f"batch_{key}_{datetime.fromtimestamp(now - v_idx * 14 * 86400).strftime('%Y%m%d_%H%M%S')}.json"
                cases[f"cases/{key}/{case_name}.py::{case_name}"] = {
                    "nodeid": f"cases/{key}/{case_name}.py::{case_name}",
                    "case_name": case_name,
                    "module": module,
                    "execution_steps": f"安装检查 → 上线 → 执行 {case_name} → 断言",
                    "passed": passed,
                    "latest_passed_report": report if passed else "",
                    "latest_report": report,
                }
            records[key][version] = {
                "version": version,
                "platform": key,
                "created_at": now - v_idx * 14 * 86400,
                "updated_at": now - v_idx * 14 * 86400 + 3600,
                "cases": cases,
            }
    path = data_dir / "version_records.json"
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 代理规则

def _seed_proxy_rules(data_dir: Path) -> None:
    rules = [
        {
            "id": "rule_demo_modify_reply",
            "name": "改写回复消息（演示）",
            "direction": "server_to_client",
            "match_field": "type",
            "match_value": "reply-message",
            "match_regex": "",
            "action": "modify",
            "modify_field": "data.msg_list",
            "modify_value": [{"record_id": "demo-001", "type": "TEXT", "content": "mock 回复（演示）", "transfer_to_human": False}],
            "replace_body": "",
            "delay_ms": 0,
            "enabled": True,
        },
        {
            "id": "rule_demo_drop_health",
            "name": "丢弃健康上报（演示）",
            "direction": "client_to_server",
            "match_field": "type",
            "match_value": "robot-health-report",
            "match_regex": "",
            "action": "drop",
            "modify_field": "",
            "modify_value": None,
            "replace_body": "",
            "delay_ms": 0,
            "enabled": False,
        },
        {
            "id": "rule_demo_replace_banner",
            "name": "替换横幅推送（演示）",
            "direction": "server_to_client",
            "match_field": "type",
            "match_value": "banner-push",
            "match_regex": "",
            "action": "replace",
            "modify_field": "",
            "modify_value": None,
            "replace_body": json.dumps({"type": "banner-push", "data": {"content": "演示横幅", "level": "info"}}, ensure_ascii=False),
            "delay_ms": 0,
            "enabled": True,
        },
        {
            "id": "rule_demo_delay",
            "name": "延迟下行消息 500ms（演示）",
            "direction": "server_to_client",
            "match_field": "type",
            "match_value": "",
            "match_regex": "",
            "action": "delay",
            "modify_field": "",
            "modify_value": None,
            "replace_body": "",
            "delay_ms": 500,
            "enabled": False,
        },
    ]
    path = data_dir / "proxy_rules.json"
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 定时任务

def _seed_schedules(data_dir: Path) -> None:
    now = datetime.now()
    schedules = [
        {
            "id": "sch_demo_nightly",
            "name": "夜间回归（平台A）",
            "enabled": True,
            "spec": {"type": "daily", "time": "02:00"},
            "target_machine": "10.0.0.11",
            "platform": "platform_a",
            "cases": ["cases/platform_a/"],
            "plan": {},
            "created_at": (now - timedelta(days=21)).isoformat(timespec="seconds"),
            "next_run_at": (now + timedelta(hours=6)).isoformat(timespec="seconds"),
            "last_triggered_at": (now - timedelta(days=1)).isoformat(timespec="seconds"),
            "last_run": {"task_id": "a1b2c3d4e5f6", "status": "success", "at": (now - timedelta(days=1)).isoformat(timespec="seconds"), "error": None},
        },
        {
            "id": "sch_demo_weekly",
            "name": "周一全量回归（平台B）",
            "enabled": True,
            "spec": {"type": "weekly", "time": "03:30", "weekdays": [1]},
            "target_machine": "10.0.0.12",
            "platform": "platform_b",
            "cases": ["cases/platform_b/"],
            "plan": {},
            "created_at": (now - timedelta(days=14)).isoformat(timespec="seconds"),
            "next_run_at": (now + timedelta(days=2)).isoformat(timespec="seconds"),
            "last_triggered_at": (now - timedelta(days=6)).isoformat(timespec="seconds"),
            "last_run": {"task_id": "b2c3d4e5f6a7", "status": "success", "at": (now - timedelta(days=6)).isoformat(timespec="seconds"), "error": None},
        },
        {
            "id": "sch_demo_interval",
            "name": "每小时冒烟（平台C）",
            "enabled": False,
            "spec": {"type": "interval", "interval_hours": 1},
            "target_machine": "10.0.0.13",
            "platform": "platform_c",
            "cases": ["cases/platform_c/test_install_rpa_smoke.py"],
            "plan": {},
            "created_at": (now - timedelta(days=7)).isoformat(timespec="seconds"),
            "next_run_at": (now + timedelta(hours=1)).isoformat(timespec="seconds"),
            "last_triggered_at": (now - timedelta(days=1)).isoformat(timespec="seconds"),
            "last_run": None,
        },
    ]
    path = data_dir / "schedules.json"
    path.write_text(json.dumps({"schedules": schedules}, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 历史报告

def _seed_results(results_dir: Path, keys: list[str]) -> None:
    """生成 12 份历史执行报告（每平台 4 份）+ 对应日志，时间分布在过去 14 天。"""
    json_dir = results_dir / "json"
    log_dir = results_dir / "logs"
    json_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    for key in keys:
        version = _PLATFORM_VERSIONS.get(key, ["1.0.0"])[0]
        for i in range(4):
            run_ts = _now_ts() - (i * 3 + _RNG.randint(0, 20)) * 86400
            ts_str = datetime.fromtimestamp(run_ts).strftime("%Y%m%d_%H%M%S")
            label = datetime.fromtimestamp(run_ts).strftime("%Y-%m-%d %H:%M:%S")
            filename = f"batch_{key}_{ts_str}.json"

            tests = []
            for module, case_name in _CASES.get(key, []):
                duration = round(_RNG.uniform(0.5, 12.0), 3)
                r = _RNG.random()
                outcome = "passed" if r > 0.12 else ("failed" if r > 0.05 else "skipped")
                tests.append({
                    "nodeid": f"cases/{key}/{case_name}.py::{case_name}",
                    "case_name": case_name,
                    "module": module,
                    "outcome": outcome,
                    "duration": duration,
                    "skipped": None if outcome != "skipped" else "条件不满足（演示）",
                    "traceback": "" if outcome == "passed" else "AssertionError: 演示失败（模拟断言错误）\n  at cases/.../test_x.py:42",
                })

            summary = {
                "total": len(tests),
                "passed": sum(1 for t in tests if t["outcome"] == "passed"),
                "failed": sum(1 for t in tests if t["outcome"] == "failed"),
                "skipped": sum(1 for t in tests if t["outcome"] == "skipped"),
            }
            report = {
                "task_name": f"batch:{key}:{version}",
                "task_id": _RNG.randbytes(6).hex()[:12],
                "created": label,
                "duration": round(sum(t["duration"] for t in tests) + _RNG.uniform(2, 8), 2),
                "platform": key,
                "version": version,
                "summary": summary,
                "tests": tests,
            }
            (json_dir / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

            # 对应日志（演示格式，与源平台 test_run.log 风格一致）
            lines = [f"{label} [INFO] 开始批量执行 {key} v{version}（{summary['total']} 条用例）"]
            for t in tests:
                icon = "[OK]" if t["outcome"] == "passed" else ("[!]" if t["outcome"] == "failed" else "[SKIP]")
                lines.append(f"{label} {icon} {t['case_name']} ({t['duration']}s)")
            lines.append(f"{label} [Latency] p50={_RNG.randint(40, 90)}ms p95={_RNG.randint(120, 300)}ms max={_RNG.randint(300, 900)}ms")
            lines.append(f"{label} [结果] 通过 {summary['passed']} / 失败 {summary['failed']} / 跳过 {summary['skipped']}")
            (log_dir / filename.replace(".json", ".log")).write_text("\n".join(lines), encoding="utf-8")
