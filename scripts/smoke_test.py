"""AT Web 全端点冒烟测试（SSE 安全版）。

覆盖：
- 13 个模块的核心端点（GET/POST/PUT/DELETE）
- 远程任务提交 → 真实 DemoEngine 执行 → 状态/日志/结果
- 本地批量执行
- 定时任务 CRUD + 手动触发（验证不覆盖其他条目）
- SSE /api/ui/events 有界读取（最多 3 帧即断开，不阻塞）

用法: .venv/Scripts/python scripts/smoke_test.py
退出码: 0=全部通过, 1=存在失败
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import AppConfig  # noqa: E402
from server import create_app  # noqa: E402

PASSED = 0
FAILED = 0
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED += 1
        FAILURES.append(f"{name} {detail}")
        print(f"  [FAIL] {name} {detail}")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    app = create_app(AppConfig.load_from_project(root))
    c = app.test_client()

    # ---- 认证 ----
    r = c.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    check("login 拒绝错误密码", r.status_code == 401)
    r = c.post("/api/auth/login", json={"username": "admin", "password": "demo123"})
    check("login 成功", r.status_code == 200 and r.get_json().get("ok"))
    r = c.get("/api/auth/me")
    check("auth/me", r.status_code == 200 and r.get_json().get("user") == "admin")
    r = c.get("/api/cases/")  # 已登录
    check("鉴权守卫（登录后放行）", r.status_code == 200)
    c.post("/api/auth/logout")
    r = c.get("/api/cases/")
    check("鉴权守卫（登出后 401）", r.status_code == 401)
    c.post("/api/auth/login", json={"username": "admin", "password": "demo123"})

    # ---- 基础只读端点 ----
    r = c.get("/health")
    check("health", r.status_code == 200 and r.get_json().get("status") == "ok")

    r = c.get("/api/cases/")
    cases = r.get_json()
    check("cases 列表有数据", r.status_code == 200 and len(cases) > 10, f"count={len(cases)}")

    r = c.get("/api/cases/modules")
    check("cases/modules 分组", r.status_code == 200 and len(r.get_json()) >= 4)

    r = c.get("/api/cases/marks")
    check("cases/marks", r.status_code == 200 and len(r.get_json()) > 0)

    first = cases[0]
    r = c.get(f"/api/cases/collect?case={first['path']}")
    check("cases/collect 子场景", r.status_code == 200 and r.get_json().get("total", 0) >= 1)

    r = c.get("/api/cases/with-mark?mark=smoke")
    check("cases/with-mark", r.status_code == 200 and len(r.get_json().get("files", [])) > 0)

    r = c.get("/api/cases/history")
    hist = r.get_json()
    check("cases/history 历史报告", r.status_code == 200 and len(hist) >= 4, f"count={len(hist)}")
    if hist:
        r = c.get(f"/api/cases/history/{hist[0]['file']}")
        check("cases/history 详情", r.status_code == 200 and bool(r.get_json().get("tests")))
        if hist[0].get("log_file"):
            r = c.get(f"/api/cases/log/{hist[0]['log_file']}")
            check("cases/log 日志文件", r.status_code == 200 and len(r.data) > 50)

    r = c.get("/api/tasks/remote-list")
    check("tasks/remote-list 种子", r.status_code == 200 and len(r.get_json()) >= 3)
    r = c.get("/api/cases/remote-index")
    check("cases/remote-index", r.status_code == 200 and isinstance(r.get_json(), list))

    # ---- 任务 ----
    r = c.get("/api/tasks/")
    check("tasks 列表", r.status_code == 200)

    r = c.post("/api/tasks/demo")
    demo_tid = r.get_json().get("task_id")
    check("tasks/demo 提交", r.status_code == 202 and bool(demo_tid))
    for _ in range(30):
        time.sleep(0.5)
        d = c.get(f"/api/tasks/{demo_tid}").get_json()
        if d.get("status") in ("success", "failed"):
            break
    check("demo 任务完成", d.get("status") == "success", f"status={d.get('status')}")

    # ---- 远程任务（DemoEngine 真实执行）----
    r = c.post("/api/tasks/submit", json={
        "target_machine": "10.0.0.12", "platform": "platform_a",
        "cases": ["cases/platform_a/test_install_rpa_smoke.py"]})
    j = r.get_json()
    check("tasks/submit 提交", r.status_code == 200 and j.get("success"), str(j))
    tid = j["task_id"]
    d = None
    for _ in range(90):
        time.sleep(1)
        d = c.get(f"/api/tasks/{tid}/status").get_json()
        if d.get("status") in ("success", "failed", "stopped"):
            break
    check("远程任务执行完成", d is not None and d.get("status") in ("success", "failed", "stopped"),
          f"status={d.get('status') if d else 'None'}")

    r = c.get(f"/api/tasks/{tid}/log?limit=200")
    lg = r.get_json()
    check("远程任务日志", r.status_code == 200 and lg.get("total", 0) >= 5 and lg.get("finished"))

    r = c.get(f"/api/tasks/{tid}/result")
    res = r.get_json()
    check("远程任务结果报告", r.status_code == 200 and isinstance(res, dict) and bool(res.get("summary")),
          str(res)[:80])

    # 取消一个长跑任务
    r = c.post("/api/tasks/submit", json={
        "target_machine": "10.0.0.13", "platform": "platform_b",
        "cases": ["cases/platform_b/"]})
    tid2 = r.get_json()["task_id"]
    time.sleep(1.0)
    r = c.post(f"/api/tasks/{tid2}/cancel")
    check("任务取消", r.status_code == 200 and r.get_json().get("success"))
    for _ in range(30):
        time.sleep(0.5)
        d2 = c.get(f"/api/tasks/{tid2}/status").get_json()
        if d2.get("status") in ("success", "failed", "stopped"):
            break
    check("取消后任务终止", d2.get("status") == "stopped", f"status={d2.get('status')}")
    c.post("/api/tasks/remote-remove", json={"task_id": tid2})

    # ---- 本地批量执行 ----
    r = c.post("/api/cases/execute-batch", json={
        "targets": ["cases/platform_c/test_install_rpa_smoke.py"]})
    bid = r.get_json().get("task_id")
    check("cases/execute-batch", r.status_code == 202 and bool(bid))
    for _ in range(60):
        time.sleep(1)
        d = c.get(f"/api/tasks/{bid}").get_json()
        if d.get("status") in ("success", "failed"):
            break
    check("本地批量完成", d.get("status") in ("success", "failed"))

    r = c.get("/api/cases/live-log/" + bid)
    check("cases/live-log", r.status_code == 200)

    # ---- 测试计划 ----
    r = c.get("/api/plan/")
    plan_j = r.get_json()
    check("plan 读取", r.status_code == 200 and bool(plan_j.get("plan")))
    new_plan = plan_j["plan"]
    new_plan["platform_a"]["version"] = "9.9.9-test"
    r = c.put("/api/plan/", json={"plan": new_plan})
    check("plan 保存", r.status_code == 200 and r.get_json().get("success"))
    r = c.get("/api/plan/")
    check("plan 保存生效", r.get_json()["plan"]["platform_a"]["version"] == "9.9.9-test")
    new_plan["platform_a"]["version"] = "1.4.2"
    c.put("/api/plan/", json={"plan": new_plan})
    r = c.get("/api/plan/options")
    check("plan/options 店铺+Agent", r.status_code == 200 and bool(r.get_json().get("options")))

    # ---- 机器 ----
    r = c.get("/api/machines/list")
    mj = r.get_json()
    check("machines 列表", r.status_code == 200 and mj["summary"]["total"] >= 5,
          f"total={mj['summary']['total']}")
    check("machines 含离线机", any(m["ip"] == "10.0.0.14" and not m["available"] for m in mj["data"]))
    r = c.post("/api/machines/add", json={"ip": "10.0.0.99", "label": "临时机"})
    check("machines 添加", r.status_code == 200 and r.get_json().get("success"))
    r = c.post("/api/machines/remove", json={"ip": "10.0.0.99"})
    check("machines 移除", r.status_code == 200 and r.get_json().get("success"))
    r = c.get("/api/machines/check?ip=10.0.0.15")
    check("machines 探测", r.status_code == 200 and r.get_json().get("available") is True)
    r = c.get("/api/machines/diff?ip=10.0.0.12")
    check("machines diff", r.status_code == 200 and r.get_json().get("behind") == 0)
    r = c.post("/api/machines/update", json={"target": "10.0.0.12"})
    upd = r.get_json().get("update_id")
    check("machines 触发更新", r.status_code == 200 and bool(upd))
    time.sleep(3.0)
    r = c.get(f"/api/machines/update-status/{upd}")
    check("machines 更新状态", r.status_code == 200 and r.get_json().get("status") == "success")
    r = c.get(f"/api/machines/update-log/{upd}")
    check("machines 更新日志", r.status_code == 200 and len(r.get_json().get("lines", [])) >= 5)

    # ---- 环境 ----
    r = c.get("/api/env/status")
    check("env/status", r.status_code == 200 and r.get_json().get("ready") is True)
    r = c.get("/api/env/accounts")
    check("env/accounts", r.status_code == 200 and bool(r.get_json().get("accounts")))
    r = c.get("/api/env/versions?platform=platform_a")
    check("env/versions", r.status_code == 200 and len(r.get_json().get("versions", [])) >= 3)
    r = c.get("/api/env/users")
    check("env/users 演示账号", r.status_code == 200 and len(r.get_json().get("users", [])) >= 4)
    r = c.post("/api/env/install-rpa", json={"platform": "platform_a", "version": "1.4.2"})
    check("env/install-rpa", r.status_code == 200 and r.get_json().get("success"))
    r = c.post("/api/env/online-agent", json={"platform": "platform_a", "shop": "演示店铺A", "agent": "agent_a_01"})
    check("env/online-agent", r.status_code == 200 and r.get_json().get("success"))
    r = c.post("/api/env/create-users", json={"platform": "platform_b", "count": 2})
    check("env/create-users", r.status_code == 200 and len(r.get_json().get("users", [])) == 2)
    r = c.post("/api/env/users/rescan")
    check("env/users/rescan", r.status_code == 200 and r.get_json().get("scanned", 0) >= 4)

    # ---- 健康 ----
    r = c.get("/api/health/check")
    check("health/check", r.status_code == 200 and r.get_json().get("status") == "healthy")
    r = c.get("/api/health/remote-version")
    check("health/remote-version", r.status_code == 200)
    r = c.get("/api/health/code-diff")
    check("health/code-diff", r.status_code == 200 and r.get_json().get("behind") == 0)

    # ---- 代理规则 ----
    r = c.get("/api/proxy/status")
    check("proxy 状态", r.status_code == 200 and r.get_json().get("running") is True)
    r = c.get("/api/proxy/flows")
    check("proxy 活跃连接", r.status_code == 200 and isinstance(r.get_json(), list))
    r = c.get("/api/proxy/rules")
    rules = r.get_json()
    check("proxy 规则列表", r.status_code == 200 and len(rules) >= 4)
    new_rule = dict(rules[0])
    new_rule["id"] = "rule_smoke_test"
    new_rule["name"] = "冒烟测试规则"
    r = c.post("/api/proxy/rules", json=new_rule)
    check("proxy 新增规则", r.status_code == 200 and r.get_json().get("success"))
    r = c.put(f"/api/proxy/rules/{new_rule['id']}", json={"enabled": False})
    check("proxy 更新规则", r.status_code == 200 and r.get_json().get("success"))
    r = c.delete(f"/api/proxy/rules/{new_rule['id']}")
    check("proxy 删除规则", r.status_code == 200 and r.get_json().get("success"))
    r = c.post("/api/proxy/restart")
    check("proxy 重启", r.status_code == 200 and r.get_json().get("success"))

    # ---- Mock WS ----
    r = c.get("/api/mock_ws/status")
    check("mock_ws 初始状态", r.status_code == 200 and r.get_json().get("running") is True)
    r = c.get("/api/mock_ws/server_info")
    check("mock_ws 服务器信息", r.status_code == 200 and bool(r.get_json().get("ip")))
    r = c.post("/api/mock_ws/start")
    check("mock_ws 启动", r.status_code == 200 and r.get_json().get("ok"))
    time.sleep(3.5)
    r = c.get("/api/mock_ws/status")
    check("mock_ws 运行中+日志", r.get_json().get("running") is True and r.get_json().get("log_seq", 0) >= 1)
    r = c.get("/api/mock_ws/logs?after=0")
    check("mock_ws 日志流", r.status_code == 200 and len(r.get_json().get("logs", [])) >= 1)
    r = c.get("/api/mock_ws/templates")
    check("mock_ws 模板", r.status_code == 200 and len(r.get_json().get("templates", [])) >= 3)
    tpl = r.get_json()["templates"][0]["key"]
    r = c.post("/api/mock_ws/preview", json={"template": tpl, "params": {}})
    check("mock_ws 模板预览", r.status_code == 200 and r.get_json().get("ok"))
    r = c.post("/api/mock_ws/send", json={"message": {"type": "reply-message", "data": {"msg_list": []}}})
    check("mock_ws 下发", r.status_code == 200 and r.get_json().get("ok"))
    r = c.post("/api/mock_ws/stop")
    check("mock_ws 停止", r.status_code == 200 and r.get_json().get("ok"))

    # ---- 弱网工具（演示） ----
    r = c.get("/api/clumsy/status")
    check("clumsy 初始状态", r.status_code == 200 and r.get_json().get("running") is False)
    r = c.get("/api/clumsy/presets")
    check("clumsy 预设", r.status_code == 200 and len(r.get_json()) >= 8)
    r = c.get("/api/clumsy/installation")
    check("clumsy 安装状态", r.status_code == 200 and r.get_json().get("installed") is True)
    r = c.post("/api/clumsy/start", json={"preset": "2g"})
    check("clumsy 预设启动", r.status_code == 200 and r.get_json().get("success"))
    r = c.get("/api/clumsy/status")
    check("clumsy 运行中", r.get_json().get("running") is True and r.get_json().get("pid"))
    r = c.post("/api/clumsy/validate", json={"config": {"filter_rule": "tcp.DstPort == 8765", "lag_enabled": True, "lag_time": 300}})
    check("clumsy 配置校验", r.status_code == 200 and r.get_json().get("valid") is True)
    r = c.post("/api/clumsy/stop")
    check("clumsy 停止", r.status_code == 200 and r.get_json().get("success"))

    # ---- 定时任务 ----
    r = c.get("/api/schedules")
    before = len(r.get_json()["schedules"])
    check("schedules 种子", r.status_code == 200 and before >= 3, f"count={before}")
    r = c.post("/api/schedules", json={
        "name": "冒烟临时任务", "spec": {"type": "daily", "time": "23:59"},
        "target_machine": "10.0.0.11", "platform": "platform_a",
        "cases": ["cases/platform_a/test_install_rpa_smoke.py"]})
    sch_id = r.get_json()["id"]
    check("schedules 创建", r.status_code == 201 and bool(sch_id))
    r = c.get("/api/schedules")
    check("schedules 创建不丢旧数据", len(r.get_json()["schedules"]) == before + 1)
    r = c.post(f"/api/schedules/{sch_id}/run")
    check("schedules 手动触发", r.status_code == 200 and r.get_json().get("success"))
    r = c.get("/api/schedules")
    all_sch = r.get_json()["schedules"]
    check("schedules 触发不覆盖列表", len(all_sch) == before + 1)
    trig = next(s for s in all_sch if s["id"] == sch_id)
    check("schedules last_run 已记录", bool((trig.get("last_run") or {}).get("task_id")))
    r = c.put(f"/api/schedules/{sch_id}", json={"enabled": False})
    check("schedules 更新", r.status_code == 200 and r.get_json().get("enabled") is False)
    r = c.delete(f"/api/schedules/{sch_id}")
    check("schedules 删除", r.status_code == 200)

    # ---- UI 接口测试 ----
    r = c.get("/api/ui/messages?limit=5")
    check("ui 消息帧", r.status_code == 200 and isinstance(r.get_json(), list))
    r = c.get("/api/ui/phrases")
    check("ui 话术库", r.status_code == 200 and len(r.get_json()) >= 5)
    r = c.get("/api/ui/random-phrase")
    check("ui 随机话术", r.status_code == 200 and bool(r.get_json().get("phrase")))
    r = c.get("/api/ui/assets")
    check("ui 素材池", r.status_code == 200 and len(r.get_json().get("images", [])) >= 6)
    r = c.get("/api/ui/active-conversations")
    check("ui 活跃会话", r.status_code == 200 and len(r.get_json()) >= 4)
    r = c.post("/api/ui/send-card", json={"user_name": "演示买家小王", "channel": "platform_a"})
    check("ui send-card", r.status_code == 200 and r.get_json().get("success"))
    r = c.post("/api/ui/send-batch", json={"ports": [7001, 7002], "total_rounds": 1,
                                           "message_type": "text", "send_interval": 0.1})
    btid = r.get_json().get("task_id")
    check("ui send-batch 提交", r.status_code == 200 and bool(btid))
    for _ in range(40):
        time.sleep(0.25)
        bs = c.get(f"/api/ui/send-batch/{btid}/status").get_json()
        if bs.get("status") in ("completed", "stopped"):
            break
    check("ui send-batch 完成", bs.get("status") == "completed" and bs.get("sent") >= 2, str(bs))

    # SSE 有界读取（最多 3 帧即断开，避免无限流阻塞）
    with c.get("/api/ui/events") as resp:
        ctype = resp.headers.get("Content-Type", "")
        check("SSE content-type", "text/event-stream" in ctype)
        got = 0
        for chunk in resp.response:
            txt = chunk.decode("utf-8", "replace")
            if txt.startswith("data:"):
                got += 1
            if got >= 3:
                break
        check("SSE 收到消息帧", got >= 3, f"got={got}")

    # ---- 版本记录 ----
    r = c.get("/api/version-records/platforms")
    vr_p = r.get_json()
    check("version-records 平台列表", r.status_code == 200 and len(vr_p) >= 3, f"count={len(vr_p)}")
    r = c.get(f"/api/version-records/{vr_p[0]}/versions")
    vr_v = r.get_json()
    check("version-records 版本列表", r.status_code == 200 and len(vr_v) >= 3)
    ver = vr_v[0]["version"]
    r = c.get(f"/api/version-records/{vr_p[0]}/{ver}")
    vr_d = r.get_json()
    check("version-records 用例明细", r.status_code == 200 and len(vr_d.get("cases", [])) >= 5
          and vr_d["summary"]["total"] > 0)
    node = vr_d["cases"][0]
    r = c.post(f"/api/version-records/{vr_p[0]}/{ver}", json={
        "nodeid": "smoke::test_smoke_case", "case_name": "test_smoke_case",
        "module": "smoke", "passed": True})
    check("version-records upsert", r.status_code == 200 and r.get_json().get("success"))

    # ---- 配置 ----
    r = c.get("/api/config/files")
    cfg_files = r.get_json().get("files", [])
    check("config 文件列表", r.status_code == 200 and len(cfg_files) >= 5,
          f"count={len(cfg_files)}")
    target = next(f for f in cfg_files if f["path"] == "main/config.yaml")
    r = c.get(f"/api/config/file?path={target['path']}")
    raw = r.get_json().get("raw", "")
    check("config 读取文件", r.status_code == 200 and "current_env" in raw)
    r = c.put("/api/config/file", json={"path": target["path"], "raw": raw})
    check("config 保存文件", r.status_code == 200 and r.get_json().get("success"))
    r = c.get("/api/config/file?path=../../etc/passwd")
    check("config 路径穿越拒绝", r.status_code == 400)

    # ---- 外链占位页 ----
    for key in ("vm-console", "minio"):
        r = c.get(f"/ext/{key}")
        check(f"ext/{key} 占位页", r.status_code == 200 and b"DEMO" in r.data)

    # ---- 汇总 ----
    print()
    print(f"===== 冒烟测试: {PASSED} 通过 / {FAILED} 失败 =====")
    if FAILURES:
        print("失败项:")
        for f in FAILURES:
            print(f"  - {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
