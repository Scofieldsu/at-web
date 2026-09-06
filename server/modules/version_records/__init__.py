"""版本测试记录 — 按平台+版本追踪每条用例的通过状态与报告链接。

数据持久化到 var/data/version_records.json（seed 预置 3 平台 × 4 版本）。
前端 VersionRecords 页消费：
  GET /api/version-records/platforms          → [platform, ...]
  GET /api/version-records/<p>/versions       → [{version, ...}, ...]
  GET /api/version-records/<p>/<version>      → {cases: {...}, summary}
  POST /api/version-records/<p>/<version>     → 新增/覆盖一条用例状态
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("version_records", __name__, url_prefix="/api/version-records")

logger = get_logger(__name__)


def _file() -> Path:
    return Path(current_app.config["PROJECT_ROOT"]) / "var" / "data" / "version_records.json"


def _load() -> dict:
    f = _file()
    if not f.exists():
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


def _platforms() -> list[str]:
    return [p["key"] for p in current_app.config.get("PLATFORMS", [])]


@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "version_records", "platforms": _platforms()})


@bp.route("/platforms", methods=["GET"])
def list_platforms():
    data = _load()
    # 以数据里实际存在的平台为准（与配置平台取并集）
    out = [p for p in _platforms() if p in data]
    for p in data:
        if p not in out:
            out.append(p)
    return jsonify(out)


@bp.route("/<platform>/versions", methods=["GET"])
def list_versions(platform: str):
    """该平台所有版本的概要（含通过率），最新在前。"""
    data = _load()
    versions = data.get(platform, {})
    out = []
    for ver, rec in versions.items():
        cases = rec.get("cases", {})
        total = len(cases)
        passed = sum(1 for c in cases.values() if c.get("passed"))
        out.append({
            "version": ver,
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
            "updated_at": rec.get("updated_at"),
        })
    out.sort(key=lambda v: v["updated_at"] or 0, reverse=True)
    return jsonify(out)


@bp.route("/<platform>/<version>", methods=["GET"])
def get_records(platform: str, version: str):
    """某平台某版本的用例级状态明细 + 汇总。"""
    data = _load()
    rec = data.get(platform, {}).get(version)
    if rec is None:
        return jsonify({"error": "记录不存在"}), 404
    cases = rec.get("cases", {})
    passed = sum(1 for c in cases.values() if c.get("passed"))
    return jsonify({
        "platform": platform,
        "version": version,
        "created_at": rec.get("created_at"),
        "updated_at": rec.get("updated_at"),
        "cases": list(cases.values()),
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
            "pass_rate": round(passed / len(cases) * 100, 1) if cases else 0,
        },
    })


@bp.route("/<platform>/<version>", methods=["POST"])
def upsert_case(platform: str, version: str):
    """新增/覆盖一条用例状态。Body: {nodeid, case_name, module, passed, report}"""
    data = request.get_json(force=True, silent=True) or {}
    nodeid = data.get("nodeid") or data.get("case_name", "")
    if not nodeid:
        return jsonify({"error": "nodeid 必填"}), 400

    all_data = _load()
    plat = all_data.setdefault(platform, {})
    rec = plat.setdefault(version, {
        "version": version,
        "platform": platform,
        "created_at": time.time(),
        "updated_at": time.time(),
        "cases": {},
    })
    case = rec["cases"].setdefault(nodeid, {
        "nodeid": nodeid,
        "case_name": data.get("case_name", nodeid.split("::")[-1]),
        "module": data.get("module", ""),
        "execution_steps": data.get("execution_steps", ""),
    })
    case["passed"] = bool(data.get("passed", False))
    if data.get("report"):
        case["latest_passed_report"] = data["report"]
    rec["updated_at"] = time.time()
    _save(all_data)
    return jsonify({"success": True, "case": case})
