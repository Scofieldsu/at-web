"""Mock 中控服务管理模块 — 演示版：模拟 WS 服务启停 + 模板 CRUD + 收发日志流。

源平台此模块驱动真实 mock WS 服务；通用框架版保留相同 API 契约：
- 启停为内存状态机，运行期间后台线程周期性产生演示连接/消息日志
- 模板来自 config/mock_templates.json（seed 预置）
- 日志为增量拉取（after=seq），前端轮询
"""
from __future__ import annotations

import json
import random
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("mock_ws", __name__, url_prefix="/api/mock_ws")

logger = get_logger(__name__)

_lock = threading.RLock()
_rng = random.Random(21)

# 演示买家昵称（假数据）
_NICKS = ["演示买家小王", "演示买家阿珍", "演示买家老李", "演示买家小张",
          "演示买家阿强", "演示买家婷婷", "演示买家大刘", "演示买家小雨"]
# 演示平台 channel
_CHANNELS = ["platform_a", "platform_b", "platform_c"]
_PRODUCTS = [
    ("demo-sku-001", "演示商品：无线蓝牙耳机"),
    ("demo-sku-002", "演示商品：便携充电宝"),
    ("demo-sku-003", "演示商品：智能水杯"),
]

# 状态机
_state: dict = {
    "running": False,
    "started_at": None,
    "connections": [],   # [{cid, channel, nick}]
}
_logs: list[dict] = []
_seq = 0
_worker: threading.Thread | None = None


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _templates_file() -> Path:
    try:
        from server import runtime
        root = runtime.project_root()
    except Exception:  # noqa: BLE001 — 回退到请求上下文
        root = Path(current_app.config["PROJECT_ROOT"])
    return root / "config" / "mock_templates.json"


def _load_templates() -> list[dict]:
    """读取模板（兼容两种存储格式）。

    - list：按序返回
    - dict：按 key 索引（含 ``_`` 开头的说明键会被跳过）→ 转 list
    """
    f = _templates_file()
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)]
    return []


def _append_log(direction: str, kind: str, summary: str,
                msg_type: str = "", raw: str = "", channel: str = "") -> dict:
    global _seq
    with _lock:
        _seq += 1
        item = {
            "seq": _seq,
            "ts": _now(),
            "direction": direction,
            "kind": kind,
            "summary": summary,
            "msg_type": msg_type,
            "raw": raw[:2000],
            "channel": channel,
        }
        _logs.append(item)
        if len(_logs) > 2000:
            del _logs[:500]
        return item


def _render_template(tpl: dict, params: dict) -> dict:
    """按模板构造报文（演示报文结构）。"""
    msg = {"type": tpl.get("frame_type", "reply-message"), "data": {}}
    for key, default in (tpl.get("data_fields") or {}).items():
        value = params.get(key, default)
        msg["data"][key] = value
    return msg


def _worker_loop():
    """运行期间周期性产生演示日志（连接、消息）。"""
    global _seq
    while True:
        if not _state["running"]:
            return
        time.sleep(_rng.uniform(2.0, 4.0))
        with _lock:
            running = _state["running"]
            conns = list(_state["connections"])
        if not running:
            return
        r = _rng.random()
        if r < 0.15 and len(conns) < 4:
            cid = f"cid_{uuid.uuid4().hex[:8]}"
            channel = _rng.choice(_CHANNELS)
            nick = _rng.choice(_NICKS)
            conns.append({"cid": cid, "channel": channel, "nick": nick})
            _state["connections"] = conns
            _append_log("recv", "connect", f"{nick} 建立 WS 连接（{channel}）",
                        channel=channel)
        elif r < 0.3 and conns:
            victim = _rng.choice(conns)
            conns.remove(victim)
            _state["connections"] = conns
            _append_log("recv", "disconnect", f"{victim['nick']} 断开连接（{victim['channel']}）",
                        channel=victim["channel"])
        elif conns:
            conn = _rng.choice(conns)
            msg_type = _rng.choice(["customer-question", "order-notify", "system-notice"])
            product_id, product_name = _rng.choice(_PRODUCTS)
            content = _rng.choice([
                "请问这款有货吗？",
                "什么时候发货？",
                "能便宜点吗？",
                "怎么还没收到货？",
                "我要转人工客服",
            ])
            payload = {
                "type": msg_type,
                "data": {
                    "user_name": conn["nick"],
                    "conversation_id": f"conv_{uuid.uuid4().hex[:8]}",
                    "content": content,
                    "product_id": product_id,
                    "product_name": product_name,
                },
            }
            item = _append_log("recv", "frame", f"{conn['nick']}: {content}",
                               msg_type=msg_type,
                               raw=json.dumps(payload, ensure_ascii=False),
                               channel=conn["channel"])
            # 自动回复（send 方向）
            if _rng.random() < 0.7:
                reply = {
                    "type": "reply-message",
                    "data": {"msg_list": [{"record_id": uuid.uuid4().hex[:12],
                                           "type": "TEXT",
                                           "content": "您好，感谢您的咨询（演示自动回复）"}]},
                }
                _append_log("send", "frame", f"自动回复 → {conn['nick']}",
                            msg_type="reply-message",
                            raw=json.dumps(reply, ensure_ascii=False),
                            channel=conn["channel"])


def _ensure_worker():
    global _worker
    if _state["running"] and _worker is not None and _worker.is_alive():
        return
    _worker = threading.Thread(target=_worker_loop, daemon=True)
    _worker.start()


def auto_start() -> None:
    """后端启动时自动启动 Mock 服务（演示：页面默认运行中，消息流/连接默认有数据）。"""
    with _lock:
        if _state["running"]:
            return
        _state["running"] = True
        _state["started_at"] = time.time()
    _ensure_worker()
    _append_log("recv", "system", "Mock WS 服务已启动（自动启动，演示）")
    logger.info("Mock WS 自动启动（演示）")


@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "mock_ws", "running": _state["running"]})


@bp.route("/status", methods=["GET"])
def status():
    """Mock 服务状态。"""
    with _lock:
        conns = list(_state["connections"])
        uptime = (time.time() - _state["started_at"]) if _state["started_at"] else 0
    return jsonify({
        "running": _state["running"],
        "uptime": int(uptime),
        "rpa_connections": [
            {k: v for k, v in c.items()} for c in conns
        ],
        "log_seq": _seq,
    })


@bp.route("/start", methods=["POST"])
def start():
    """启动 mock 服务（演示）。"""
    with _lock:
        if _state["running"]:
            return jsonify({"ok": True, "message": "已在运行"})
        _state["running"] = True
        _state["started_at"] = time.time()
    _ensure_worker()
    _append_log("recv", "system", "Mock WS 服务已启动（演示）")
    logger.info("Mock WS 启动（演示）")
    return jsonify({"ok": True, "message": "已启动（演示）"})


@bp.route("/stop", methods=["POST"])
def stop():
    """停止 mock 服务（演示）。"""
    with _lock:
        if not _state["running"]:
            return jsonify({"ok": True, "message": "未在运行"})
        _state["running"] = False
        _state["started_at"] = None
        _state["connections"] = []
    _append_log("recv", "system", "Mock WS 服务已停止（演示）")
    logger.info("Mock WS 停止（演示）")
    return jsonify({"ok": True, "message": "已停止（演示）"})


@bp.route("/templates", methods=["GET"])
def templates():
    """消息模板列表。"""
    return jsonify({"templates": _load_templates()})


@bp.route("/image_urls", methods=["GET"])
def image_urls():
    """图片 URL 列表（演示占位图）。"""
    return jsonify({"images": [f"/static/demo_img_{i}.png" for i in range(1, 6)]})


def _resolve_template(key: str, params: dict | None):
    for tpl in _load_templates():
        if tpl.get("key") == key:
            return tpl, (params or {})
    return None, None


@bp.route("/preview", methods=["POST"])
def preview():
    """预览模板构造的报文（不下发）。Body: {template, params}"""
    data = request.get_json(force=True, silent=True) or {}
    tpl, params = _resolve_template(data.get("template", ""), data.get("params"))
    if tpl is None:
        return jsonify({"ok": False, "error": f"模板不存在: {data.get('template')}"}), 400
    return jsonify({"ok": True, "message": _render_template(tpl, params)})


@bp.route("/send", methods=["POST"])
def send():
    """向 RPA 推送消息（演示）。Body: {template, params} 或 {message}"""
    with _lock:
        conns = list(_state["connections"])
    data = request.get_json(force=True, silent=True) or {}

    if data.get("message"):
        msg = data["message"]
        tpl_key = None
    else:
        tpl, params = _resolve_template(data.get("template", ""), data.get("params"))
        if tpl is None:
            return jsonify({"ok": False, "error": f"模板不存在: {data.get('template')}"}), 400
        msg = _render_template(tpl, params)
        tpl_key = tpl.get("key")

    raw = json.dumps(msg, ensure_ascii=False)
    sent = 0
    for conn in conns:
        _append_log("send", "frame", f"下发 {msg.get('type', '?')} → {conn['nick']}",
                    msg_type=msg.get("type", ""), raw=raw, channel=conn["channel"])
        sent += 1
    if not conns:
        # 无连接时也记一条日志，便于演示
        _append_log("send", "frame", "下发（无在线连接，仅记录）",
                    msg_type=msg.get("type", ""), raw=raw)
    logger.info("Mock 下发（演示）: %s → %d/%d", msg.get("type"), sent, len(conns))
    return jsonify({"ok": True, "sent": sent, "connected": len(conns)})


@bp.route("/logs", methods=["GET"])
def logs():
    """增量拉取收发日志。Query: after=seq"""
    after = request.args.get("after", 0, type=int)
    with _lock:
        items = [x for x in _logs if x["seq"] > after]
    return jsonify({"logs": items})


@bp.route("/server_info", methods=["GET"])
def server_info():
    """服务器信息（演示 IP）。"""
    port = _rng.choice([8765])
    return jsonify({"ip": "10.0.0.11", "port": port})
