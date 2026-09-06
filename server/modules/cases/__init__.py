"""用例管理模块 — 用例目录浏览、子场景收集、批量执行（薄路由层）。

执行逻辑在 .service（供 tasks/schedules 模块复用）。
"""
from __future__ import annotations

import time
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from server import live_log
from server.modules.tasks.service import get_scheduler

from . import service as cases_service

bp = Blueprint("cases", __name__, url_prefix="/api/cases")

# 模块 → 描述
_MARK_DESC = {
    "smoke": "冒烟测试（安装+上线核心流程）",
    "regression": "回归测试（完整功能验证）",
    "install": "RPA 安装相关",
    "online": "Agent 上线相关",
    "message": "消息收发/Mock 回复相关",
    "transfer": "转人工相关",
    "stress": "压力测试（长时间高并发）",
    "slow": "执行时间较长的用例",
}


@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "cases", "total_cases": len(cases_service.all_cases())})


@bp.route("/", methods=["GET"])
def list_cases():
    """列出所有用例文件。Query: directory, marks(逗号分隔)"""
    directory = request.args.get("directory")
    marks_param = request.args.get("marks")
    marks_list = marks_param.split(",") if marks_param else None

    cases = cases_service.all_cases()
    if directory:
        cases = [c for c in cases if c["directory"].startswith(directory) or directory in c["path"]]
    if marks_list:
        cases = [c for c in cases if any(m in c.get("marks", []) for m in marks_list)]
    return jsonify(cases)


@bp.route("/modules", methods=["GET"])
def modules():
    """按平台+模块分组，用于批量执行。"""
    out = []
    for platform, cases in cases_service.catalog().items():
        by_module: dict[str, list] = {}
        for c in cases:
            by_module.setdefault(c["module"], []).append(c)
        for module, items in by_module.items():
            out.append({
                "module": module,
                "platform": platform,
                "dir_rel": f"cases/{platform}",
                "path": f"cases/{platform}/",
                "count": len(items),
                "label": f"{platform}/{module}",
            })
    return jsonify(out)


@bp.route("/marks", methods=["GET"])
def list_marks():
    """列出所有 mark 及描述和用例命中数。"""
    counts: dict[str, int] = {}
    for c in cases_service.all_cases():
        for m in c.get("marks", []):
            counts[m] = counts.get(m, 0) + 1
    return jsonify([{"mark": m, "desc": _MARK_DESC.get(m, ""), "count": n}
                    for m, n in sorted(counts.items())])


@bp.route("/collect", methods=["GET"])
def collect():
    """收集指定用例文件的子场景（参数化测试 id）。Query: case=<路径>"""
    case = request.args.get("case")
    if not case:
        return jsonify({"error": "case 参数必填"}), 400
    for c in cases_service.all_cases():
        if c["path"] == case:
            scenarios = [{"param_id": s, "nodeid": f"{case}::{c['name']}[{s}]"}
                         for s in c.get("scenarios", [])]
            return jsonify({
                "success": True,
                "case": case,
                "functions": [f"{case}::{c['name']}"] + [s["nodeid"] for s in scenarios],
                "scenarios": scenarios,
                "total": len(scenarios) + 1,
            })
    return jsonify({"success": False, "case": case, "functions": [], "scenarios": [],
                    "total": 0, "error": "用例不存在"}), 404


@bp.route("/with-mark", methods=["GET"])
def with_mark():
    """查找包含指定 mark 的用例文件。Query: mark=<名称>"""
    mark = request.args.get("mark", "")
    if not mark:
        return jsonify({"error": "mark 参数必填"}), 400
    files = sorted({c["path"] for c in cases_service.all_cases() if mark in c.get("marks", [])})
    return jsonify({"mark": mark, "files": files})


# ---------------------------------------------------------------- 执行

@bp.route("/execute", methods=["POST"])
def execute():
    """执行单个用例文件。Body: {"case": "cases/platform_a/test_x.py"}"""
    data = request.get_json(force=True, silent=True) or {}
    case = data.get("case")
    if not case:
        return jsonify({"error": "case 字段必填"}), 400
    matched = [c for c in cases_service.all_cases() if c["path"] == case]
    if not matched:
        return jsonify({"error": "用例不存在"}), 404
    platform = matched[0]["platform"]
    task = get_scheduler().submit(f"run:{case}",
                                  lambda t: cases_service.run_cases_task(t, platform, [case]),
                                  platform=platform, cases=[case])
    return jsonify({"task_id": task.id, "status": task.status.value}), 202


@bp.route("/execute-batch", methods=["POST"])
def execute_batch():
    """批量执行用例（本机）。Body: {"targets": [...], "name": "可选任务名"}"""
    data = request.get_json(force=True, silent=True) or {}
    targets = data.get("targets") or []
    if not targets:
        return jsonify({"error": "targets 不能为空"}), 400
    name = data.get("name", "")

    by_platform: dict[str, list[str]] = {}
    for t in targets:
        for c in cases_service.all_cases():
            if c["path"] == t:
                by_platform.setdefault(c["platform"], []).append(t)
                break
    if not by_platform:
        return jsonify({"error": "未找到匹配的用例"}), 404

    def run(task):
        for platform, paths in by_platform.items():
            cases_service.run_cases_task(task, platform, paths)
            if task.status.value == "failed":
                break

    task = get_scheduler().submit(name or f"batch:{'+'.join(by_platform)}", run,
                                  platform="+".join(by_platform), cases=targets)
    return jsonify({"task_id": task.id, "status": task.status.value}), 202


@bp.route("/live-log/<task_id>", methods=["GET"])
def live_log_api(task_id: str):
    """读取任务实时日志（前端轮询）。Query: ?tail=200"""
    tail = request.args.get("tail", 200, type=int)
    content = live_log.read(task_id, tail=tail)
    return content, 200, {"Content-Type": "text/plain; charset=utf-8"}


@bp.route("/<task_id>/result", methods=["GET"])
def get_result(task_id: str):
    task = get_scheduler().get_task(task_id)
    if task is None:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(task.result or {})


# ---------------------------------------------------------------- 历史报告

def _results_dir() -> Path:
    return Path(current_app.config["PROJECT_ROOT"]) / "var" / "results"


@bp.route("/history", methods=["GET"])
def history():
    """历史执行结果摘要列表。Query: case_name, limit(默认20), offset"""
    case_name = request.args.get("case_name")
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    json_dir = _results_dir() / "json"
    results = []
    pattern = f"*{case_name}*.json" if case_name else "*.json"
    files = sorted(json_dir.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True) \
        if json_dir.exists() else []
    total = len(files)
    for f in files[offset:offset + limit]:
        try:
            import json as _json
            report = _json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        log_file = _results_dir() / "logs" / f.with_suffix(".log").name
        results.append({
            "file": f.name,
            "case_name": report.get("task_name", f.stem),
            "task_name": report.get("task_name", ""),
            "task_id": report.get("task_id", ""),
            "created_label": report.get("created", ""),
            "platform": report.get("platform", ""),
            "log_file": log_file.name if log_file.exists() else None,
            "created": f.stat().st_mtime,
            "summary": report.get("summary", {}),
            "duration": report.get("duration", 0),
            "tests_count": len(report.get("tests", [])),
        })
    resp = jsonify(results)
    resp.headers["X-Total-Count"] = str(total)
    return resp


@bp.route("/history/<filename>", methods=["GET"])
def history_detail(filename: str):
    """单次执行的完整结果详情。"""
    import json as _json
    f = _results_dir() / "json" / filename
    if not f.exists():
        return jsonify({"error": "结果文件不存在"}), 404
    try:
        return jsonify(_json.loads(f.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return jsonify({"error": "结果文件损坏"}), 500


@bp.route("/log/<filename>", methods=["GET"])
def get_log(filename: str):
    """获取指定执行的完整日志输出（纯文本）。"""
    f = _results_dir() / "logs" / filename
    if not f.exists():
        return jsonify({"error": "日志文件不存在"}), 404
    return f.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}


@bp.route("/videos/<task_id>", methods=["GET"])
def list_videos(task_id: str):
    """列出指定任务的录屏文件（演示：空列表）。"""
    return jsonify([])


@bp.route("/clean", methods=["POST"])
def clean():
    """清理超过 keep_days 天的历史结果（默认 7 天）。"""
    data = request.get_json(force=True, silent=True) or {}
    keep_days = data.get("keep_days", 7)
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for sub in ("json", "logs"):
        d = _results_dir() / sub
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
    return jsonify({"success": True, "removed": removed, "keep_days": keep_days})


# ---------------------------------------------------------------- 远程任务（演示单机：全部本地执行）

@bp.route("/remote-index", methods=["GET"])
def remote_index():
    return jsonify(cases_service.load_remote_tasks())
