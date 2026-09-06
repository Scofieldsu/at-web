"""健康检查模块 — 本机资源/版本/服务状态（演示数据版）。

源平台此模块聚合 git 版本、psutil 资源、服务存活探测；
通用框架版保留相同的响应契约，资源数值改为受控的演示波动值，
git 版本改为固定演示版本号，不依赖 git 仓库与 psutil。
"""
from __future__ import annotations

import math
import random
import socket
import time
from datetime import datetime

from flask import Blueprint, jsonify

bp = Blueprint("health", __name__, url_prefix="/api/health")

# 演示版本信息（固定，保证集群"版本一致"的演示效果）
_DEMO_COMMIT = "9f2c1ab4"
_DEMO_DATE = "2026-08-30 10:24:00"
_DEMO_VERSION = f"at-web v1.0.0 ({_DEMO_COMMIT})"

_rng = random.Random(7)


def _demo_resources() -> dict:
    """演示资源数值 — 基于时间的缓慢波动，避免每次请求跳变太大。"""
    t = time.time() / 60.0  # 以分钟为周期缓动
    cpu = 18 + 12 * abs(math.sin(t)) + _rng.uniform(0, 4)
    mem = 42 + 8 * abs(math.sin(t / 1.7)) + _rng.uniform(0, 3)
    disk = 57.3 + 0.1 * abs(math.sin(t / 30))
    return {
        "cpu_percent": round(min(cpu, 95), 1),
        "memory_percent": round(min(mem, 90), 1),
        "disk_percent": round(disk, 1),
        "cpu_cores": 8,
        "cpu_model": "Demo CPU (8 cores)",
        "memory_total_gb": 32.0,
        "disk_total_gb": 512.0,
    }


def git_version() -> dict:
    return {
        "version": _DEMO_VERSION,
        "commit_hash": _DEMO_COMMIT,
        "commit_date": _DEMO_DATE,
        "branch": "main",
        "has_uncommitted_changes": False,
    }


def get_remote_main_version() -> dict:
    """演示：远端 main 与本机一致（版本一致标签为绿）。"""
    return {
        "commit_hash": _DEMO_COMMIT,
        "commit_date": _DEMO_DATE,
        "branch": "origin/main",
    }


@bp.route("/check", methods=["GET"])
def health_check():
    """完整健康检查接口 — 用于机器状态轮询。"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "ip": "10.0.0.11",  # 演示网段（本机条目）
        "version": _DEMO_VERSION,
        "git": git_version(),
        "resources": _demo_resources(),
        "services": {
            "mitmproxy": True,
            "python_processes": 2,
            "minio": True,
        },
        "current_task": None,
    })


@bp.route("/remote-version", methods=["GET"])
def remote_version():
    """获取远端最新版本（用于代码版本对比）。"""
    return jsonify(get_remote_main_version())


@bp.route("/code-diff", methods=["GET"])
def code_diff():
    """代码差异（演示：本机与远端完全一致，无差异）。"""
    return jsonify({
        "local_hash": _DEMO_COMMIT,
        "remote_hash": _DEMO_COMMIT,
        "behind": 0,
        "ahead": 0,
        "commits": [],
        "uncommitted_diff": "",
        "untracked_files": [],
        "has_uncommitted": False,
        "truncated": False,
    })
