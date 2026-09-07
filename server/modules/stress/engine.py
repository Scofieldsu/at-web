"""压力测试演示引擎。

模拟压测执行（演示版）：后台线程按 1s tick，按负载模型（恒并发 / 爬坡 / 阶梯 /
尖峰脉冲）生成真实的 TPS / 响应时间 / 错误率曲线与累计统计，不实际发送流量，
与项目整体的演示定位一致（DemoEngine 模式）。
"""
from __future__ import annotations

import math
import random
import threading
import time
import uuid
from datetime import datetime, timedelta

from core.logging_config import get_logger

logger = get_logger(__name__)

TICK_SECONDS = 1.0

MODEL_NAMES = {"constant": "恒并发", "ramp": "爬坡", "step": "阶梯", "spike": "尖峰脉冲"}


# ---------------------------------------------------------------- 预设

def _preset(key: str, name: str, desc: str, recommended: bool, **cfg) -> dict:
    return {
        "key": key,
        "name": name,
        "description": desc,
        "recommended": recommended,
        "config": {**cfg, "scenario": name},
    }


PRESETS = [
    _preset("smoke", "轻量冒烟", "低并发短时长，快速验证目标接口在压力下可用", False,
            model="constant", concurrency=5, duration=30),
    _preset("standard", "标准负载", "爬坡到目标并发后持续运行，观察稳态性能", True,
            model="ramp", concurrency=20, ramp_up=10, duration=300),
    _preset("peak", "峰值压测", "阶梯式加压至峰值并发，探明系统性能上限", False,
            model="step", concurrency=50, steps=3, step_interval=120, duration=600),
    _preset("endurance", "稳定性耐久", "中并发长时间运行，观察内存泄漏与稳定性", False,
            model="constant", concurrency=10, duration=3600),
]


def list_presets() -> list[dict]:
    return PRESETS


# ---------------------------------------------------------------- 引擎

class StressEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._state: dict | None = None      # 当前运行状态（None = 空闲）
        self._last_report: dict | None = None
        self._history: list[dict] = self._seed_history()

    # ---------- 对外 API ----------

    def start(self, config: dict) -> dict:
        cfg = self._normalize(config or {})
        with self._lock:
            if self._state is not None:
                return {"success": False, "error": "已有压测在运行，请先停止"}
            task_id = uuid.uuid4().hex[:12]
            self._stop_event.clear()
            self._state = {
                "task_id": task_id,
                "status": "running",
                "scenario": cfg["scenario"],
                "config": cfg,
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "started_ts": time.time(),
                "completed": 0,
                "failed": 0,
                "points": [],
                "stop_reason": "",
            }
            self._thread = threading.Thread(
                target=self._run, args=(task_id,), daemon=True, name="stress-demo")
            self._thread.start()
            logger.info("启动压测（演示）: %s %s", task_id, cfg["scenario"])
            return {"success": True, "task_id": task_id,
                    "message": f"已启动压测：{cfg['scenario']}"}

    def stop(self) -> dict:
        with self._lock:
            state = self._state
        if state is None:
            return {"success": False, "error": "当前没有运行中的压测"}
        self._stop_event.set()
        return {"success": True, "message": "已请求停止，约 1 秒内完成收尾"}

    def status(self) -> dict:
        with self._lock:
            state = self._state
            if state is None:
                last = self._last_report
                return {
                    "running": False,
                    "status": last["status"] if last else "idle",
                    "task_id": last["task_id"] if last else "",
                    "scenario": last["scenario"] if last else "",
                    "started_at": last["started_at"] if last else "",
                    "elapsed_seconds": last["duration_seconds"] if last else 0,
                    "progress": 1.0 if last else 0.0,
                    "current_concurrency": 0,
                    "target_concurrency": 0,
                    "completed": last["total"] if last else 0,
                    "failed": last["failed"] if last else 0,
                    "success_rate": last["success_rate"] if last else 100.0,
                    "stop_reason": last["stop_reason"] if last else "",
                    "last_point": None,
                    "config": None,
                }
            cfg = state["config"]
            elapsed = min(int(time.time() - state["started_ts"]), cfg["duration"])
            last_point = state["points"][-1] if state["points"] else None
            return {
                "running": True,
                "status": "running",
                "task_id": state["task_id"],
                "scenario": state["scenario"],
                "started_at": state["started_at"],
                "elapsed_seconds": elapsed,
                "progress": round(elapsed / cfg["duration"], 4) if cfg["duration"] else 0.0,
                "current_concurrency": last_point["concurrency"] if last_point else 0,
                "target_concurrency": cfg["concurrency"],
                "completed": state["completed"],
                "failed": state["failed"],
                "success_rate": last_point["success_rate"] if last_point else 100.0,
                "stop_reason": "",
                "last_point": last_point,
                "config": cfg,
            }

    def metrics(self, after: int = 0) -> list[dict]:
        """实时指标序列（?after=N 增量拉取；结束后仍可取最近一次运行的完整序列）。"""
        with self._lock:
            if self._state is not None:
                return self._state["points"][after:]
            if self._last_report is not None:
                return self._last_report["points"][after:]
            return []

    def report(self) -> dict | None:
        with self._lock:
            r = self._last_report
            if r is None:
                return None
            return {k: v for k, v in r.items() if k != "points"}

    def history(self) -> list[dict]:
        with self._lock:
            return list(self._history)

    # ---------- 内部 ----------

    @staticmethod
    def _normalize(config: dict) -> dict:
        def _i(v, d: int, lo: int, hi: int) -> int:
            try:
                return max(lo, min(hi, int(v)))
            except (TypeError, ValueError):
                return d

        model = config.get("model", "constant")
        if model not in MODEL_NAMES:
            model = "constant"
        duration = _i(config.get("duration"), 300, 5, 86400)
        cfg = {
            "model": model,
            "concurrency": _i(config.get("concurrency"), 10, 1, 500),
            "ramp_up": _i(config.get("ramp_up"), 10, 1, duration),
            "steps": _i(config.get("steps"), 3, 2, 10),
            "step_interval": _i(config.get("step_interval"), 60, 5, 86400),
            "peak": _i(config.get("peak"), 50, 2, 500),
            "peak_duration": _i(config.get("peak_duration"), 30, 5, 3600),
            "duration": duration,
            "total_requests": _i(config.get("total_requests"), 0, 0, 10_000_000),
            "think_time": _i(config.get("think_time"), 0, 0, 600_000),
            "timeout": _i(config.get("timeout"), 5, 1, 300),
            "keep_alive": bool(config.get("keep_alive", True)),
            "target_api": config.get("target_api") or "send-text",
            "target_url": config.get("target_url") or "",
            "scenario": (config.get("scenario") or "自定义场景").strip() or "自定义场景",
            "assertions": config.get("assertions") or {},
        }
        if cfg["model"] == "ramp" and cfg["ramp_up"] >= cfg["duration"]:
            cfg["ramp_up"] = max(1, cfg["duration"] // 3)
        if cfg["model"] == "spike" and cfg["peak"] <= cfg["concurrency"]:
            cfg["peak"] = cfg["concurrency"] * 2
        return cfg

    @staticmethod
    def _target_concurrency(cfg: dict, t: int) -> int:
        """按负载模型计算 t 时刻的目标并发。"""
        m = cfg["model"]
        c = cfg["concurrency"]
        if m == "constant":
            return c
        if m == "ramp":
            return max(1, round(c * min(1.0, t / cfg["ramp_up"])))
        if m == "step":
            n = min(cfg["steps"], 1 + int(t // cfg["step_interval"]))
            return max(1, round(c * n / cfg["steps"]))
        # spike：基线 concurrency，每 (peak_duration 尖峰 + peak_duration 回落) 循环
        cycle = cfg["peak_duration"] * 2
        return cfg["peak"] if (t % cycle) < cfg["peak_duration"] else max(1, round(c * 0.4))

    @staticmethod
    def _sample_latency(cfg: dict, conc: int) -> tuple[float, float, float, float, float, float]:
        """生成 (avg, p50, p90, p95, p99, err_rate)：基础响应随并发上升（模拟排队）。"""
        base = 90 + conc * 7.0
        base *= 1.0 + max(0, conc - 20) * 0.04
        avg = base * random.uniform(0.9, 1.15)
        p50 = avg * random.uniform(0.82, 0.95)
        p90 = avg * random.uniform(1.6, 2.0)
        p95 = p90 * random.uniform(1.15, 1.45)
        p99 = p95 * random.uniform(1.5, 2.2)
        err = 0.002 + max(0, conc - 30) * 0.0008
        if random.random() < 0.03:
            err += random.uniform(0.01, 0.05)  # 偶发错误尖峰
        return avg, p50, p90, p95, p99, min(err, 0.35)

    @staticmethod
    def _check_assertions(cfg: dict, point: dict) -> str:
        a = cfg.get("assertions") or {}
        if not a.get("stop_on_fail"):
            return ""
        err_rate = 100 - point["success_rate"]
        try:
            if a.get("max_error_rate") and err_rate > float(a["max_error_rate"]):
                return f"断言自动停止：错误率 {err_rate:.2f}% > 阈值 {a['max_error_rate']}%"
            if a.get("max_p95") and point["p95"] > float(a["max_p95"]):
                return f"断言自动停止：P95 {point['p95']}ms > 阈值 {a['max_p95']}ms"
            if a.get("min_success_rate") and point["success_rate"] < float(a["min_success_rate"]):
                return f"断言自动停止：成功率 {point['success_rate']}% < 阈值 {a['min_success_rate']}%"
        except (TypeError, ValueError):
            pass
        return ""

    def _tick(self, state: dict, cfg: dict, t: int) -> dict:
        conc = self._target_concurrency(cfg, t)
        avg, p50, p90, p95, p99, err_rate = self._sample_latency(cfg, conc)
        interval = max(avg / 1000.0 + cfg["think_time"] / 1000.0, 0.05)
        rps = conc / interval * random.uniform(0.92, 1.08)
        n_req = max(1, round(rps))
        errors = max(0, min(n_req, int(round(n_req * err_rate))))
        state["completed"] += n_req
        state["failed"] += errors
        return {
            "t": t,
            "concurrency": conc,
            "rps": round(rps, 1),
            "avg": round(avg),
            "p50": round(p50),
            "p90": round(p90),
            "p95": round(p95),
            "p99": round(p99),
            "errors": errors,
            "success_rate": round((n_req - errors) / n_req * 100, 2),
        }

    def _run(self, task_id: str) -> None:
        with self._lock:
            state = self._state
        if state is None or state["task_id"] != task_id:
            return
        cfg = state["config"]
        t = 0
        auto_stopped = False
        while not self._stop_event.is_set():
            t += int(TICK_SECONDS)
            point = self._tick(state, cfg, t)
            with self._lock:
                state["points"].append(point)
            if t >= cfg["duration"]:
                break
            if cfg["total_requests"] > 0 and state["completed"] >= cfg["total_requests"]:
                state["stop_reason"] = "达到目标请求数"
                break
            reason = self._check_assertions(cfg, point)
            if reason:
                state["stop_reason"] = reason
                auto_stopped = True
                break
            # 按 tick 间隔推进（wait 而非 sleep：停止请求可立即响应）
            self._stop_event.wait(TICK_SECONDS)
        if self._stop_event.is_set():
            state["status"] = "stopped"
            state["stop_reason"] = state["stop_reason"] or "手动停止"
        elif auto_stopped:
            state["status"] = "stopped"
        else:
            state["status"] = "completed"
            state["stop_reason"] = state["stop_reason"] or "正常完成"
        self._finalize()

    def _finalize(self) -> None:
        with self._lock:
            state = self._state
            if state is None:
                return
            report = self._build_report(state)
            self._last_report = {
                **report,
                "points": state["points"],
                "task_id": state["task_id"],
                "scenario": state["scenario"],
                "status": state["status"],
                "stop_reason": state["stop_reason"],
                "started_at": state["started_at"],
                "config": state["config"],
            }
            self._history.insert(0, {
                "task_id": state["task_id"],
                "started_at": state["started_at"],
                "scenario": state["scenario"],
                "model": MODEL_NAMES.get(state["config"]["model"], state["config"]["model"]),
                "concurrency": state["config"]["concurrency"],
                "duration_seconds": len(state["points"]),
                "avg_rps": report["avg_rps"],
                "avg_ms": report["avg"],
                "p95_ms": report["p95"],
                "success_rate": report["success_rate"],
                "status": state["status"],
            })
            self._history = self._history[:20]
            self._state = None
        logger.info("压测结束（演示）: %s %s", state["scenario"], state["status"])

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        vs = sorted(values)
        k = (len(vs) - 1) * pct / 100.0
        lo = math.floor(k)
        hi = math.ceil(k)
        if lo == hi:
            return vs[int(k)]
        return vs[lo] + (vs[hi] - vs[lo]) * (k - lo)

    @staticmethod
    def _histogram(report: dict) -> list[dict]:
        """按 p50/p95 拟合对数正态分布抽样，生成分档直方图。"""
        p50 = max(1.0, float(report["p50"]))
        p95 = max(p50 * 1.2, float(report["p95"]))
        sigma = max(0.18, (math.log(p95) - math.log(p50)) / 1.645)
        mu = math.log(p50) - sigma * sigma / 2
        edges = [0, 50, 100, 200, 400, 800, 1500, float("inf")]
        labels = ["0-50", "50-100", "100-200", "200-400", "400-800", "800-1500", "1500+"]
        counts = [0] * 7
        for _ in range(2000):
            v = math.exp(random.gauss(mu, sigma))
            for i in range(7):
                if v < edges[i + 1]:
                    counts[i] += 1
                    break
        total = sum(counts) or 1
        return [{"label": f"{labels[i]} ms", "count": counts[i],
                 "pct": round(counts[i] / total * 100, 1)} for i in range(7)]

    def _build_report(self, state: dict) -> dict:
        pts = state["points"]
        total = state["completed"]
        failed = state["failed"]
        avgs = [p["avg"] for p in pts]
        rps_list = [p["rps"] for p in pts]
        report = {
            "total": total,
            "success": total - failed,
            "failed": failed,
            "success_rate": round((total - failed) / total * 100, 2) if total else 100.0,
            "avg": round(sum(avgs) / len(avgs), 1) if avgs else 0,
            "min": round(min(avgs)) if avgs else 0,
            "max": round(max(avgs)) if avgs else 0,
            "p50": round(self._percentile(avgs, 50), 1),
            "p90": round(self._percentile(avgs, 90), 1),
            "p95": round(self._percentile(avgs, 95), 1),
            "p99": round(self._percentile(avgs, 99), 1),
            "avg_rps": round(sum(rps_list) / len(rps_list), 1) if rps_list else 0,
            "max_rps": round(max(rps_list), 1) if rps_list else 0,
            "max_concurrency": max((p["concurrency"] for p in pts), default=0),
            "duration_seconds": len(pts),
        }
        report["histogram"] = self._histogram(report)
        return report

    @staticmethod
    def _seed_history() -> list[dict]:
        """演示历史（冷启动即有数据，与 tasks 的 _warm_history 同思路）。"""
        base = datetime.now()

        def at(days_ago: int, hour: int, minute: int) -> str:
            return (base - timedelta(days=days_ago)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            ).strftime("%Y-%m-%d %H:%M:%S")

        return [
            {"task_id": "demo-hist-0004", "started_at": at(0, 9, 12), "scenario": "标准负载",
             "model": "爬坡", "concurrency": 20, "duration_seconds": 300,
             "avg_rps": 17.8, "avg_ms": 228, "p95_ms": 472, "success_rate": 99.61,
             "status": "completed"},
            {"task_id": "demo-hist-0003", "started_at": at(1, 15, 40), "scenario": "峰值压测",
             "model": "阶梯", "concurrency": 50, "duration_seconds": 600,
             "avg_rps": 26.4, "avg_ms": 415, "p95_ms": 980, "success_rate": 99.02,
             "status": "completed"},
            {"task_id": "demo-hist-0002", "started_at": at(2, 10, 5), "scenario": "自定义场景",
             "model": "尖峰脉冲", "concurrency": 30, "duration_seconds": 240,
             "avg_rps": 21.9, "avg_ms": 302, "p95_ms": 711, "success_rate": 99.35,
             "status": "stopped"},
            {"task_id": "demo-hist-0001", "started_at": at(3, 14, 26), "scenario": "轻量冒烟",
             "model": "恒并发", "concurrency": 5, "duration_seconds": 30,
             "avg_rps": 4.6, "avg_ms": 96, "p95_ms": 188, "success_rate": 100.0,
             "status": "completed"},
        ]


_engine: StressEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> StressEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = StressEngine()
        return _engine
