"""UI 接口测试模块 — 演示版：假会话 + 假消息帧 + SSE 实时消息流。

源平台此模块驱动真实 Playwright UI 自动化；通用框架版保留相同 API 契约：
- /ui/messages      历史消息帧列表（内存 + 周期性产生演示帧）
- /ui/events        SSE 实时消息流（嗅探页实时模式）
- /ui/phrases       话术库（config/phrases/shopping_faq.json）
- /ui/assets        演示素材池（图片/视频/卡片 URL）
- /ui/send-*        发送类接口（记录一帧 + 触发 SSE）
- /ui/send-batch    批量自动发送（后台线程 + 状态轮询）
- /ui/inject        消息注入（写入一帧）
- /ui/actions       UI 操作列表（演示）
- /ui/execute       执行 UI 操作（演示）
"""
from __future__ import annotations

import json
import random
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, request

from core.logging_config import get_logger

bp = Blueprint("ui", __name__, url_prefix="/api/ui")

logger = get_logger(__name__)

_rng = random.Random(31)

# 演示买家 / 客服
_NICKS = ["演示买家小王", "演示买家阿珍", "演示买家老李", "演示买家小张",
          "演示买家阿强", "演示买家婷婷"]
_AGENTS = ["演示客服A", "演示客服B"]
_CHANNELS = ["platform_a", "platform_b", "platform_c"]
_PRODUCTS = [
    ("demo-sku-001", "演示商品：无线蓝牙耳机"),
    ("demo-sku-002", "演示商品：便携充电宝"),
    ("demo-sku-003", "演示商品：智能水杯"),
]
_QUESTIONS = ["请问这款有货吗？", "什么时候发货？", "能便宜点吗？",
              "怎么还没收到货？", "我要转人工客服", "这个怎么用？"]
_REPLIES = ["您好，感谢您的咨询（演示）", "有货的，亲～（演示）",
            "48 小时内发货（演示）", "已为您转接人工客服（演示）"]

_lock = threading.RLock()
_messages: list[dict] = []      # 历史消息帧
_conversations: list[dict] = []  # 活跃会话
_seq = 0
_batch_tasks: dict[str, dict] = {}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _now_ts() -> float:
    return time.time()


# ---------------------------------------------------------------- 配置读取

def _phrases() -> list[dict]:
    path = Path(current_app.config["PROJECT_ROOT"]) / "config" / "phrases" / "shopping_faq.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("faq") or data.get("phrases") or []
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


# ---------------------------------------------------------------- 会话

def _ensure_conversations() -> None:
    """预置演示活跃会话。

    字段对齐前端消息注入页的活跃会话表：
    - user_name / nick_name / conversation_id / platform：注入命令自动带入
    - shop / product_name / last_active：展示用
    """
    global _conversations
    with _lock:
        if _conversations:
            return
        shops = ["演示店铺A", "演示店铺B", "演示店铺C"]
        for i in range(6):
            prod_id, prod_name = _PRODUCTS[i % len(_PRODUCTS)]
            _conversations.append({
                "conversation_id": f"conv_demo_{i + 1:03d}",
                "user_name": _NICKS[i],
                "nick_name": _NICKS[i],
                "platform": _CHANNELS[i % len(_CHANNELS)],
                "agent": _AGENTS[i % len(_AGENTS)],
                "shop": shops[i % len(shops)],
                "product_id": prod_id,
                "product_name": prod_name,
                "last_active": _now_ts() - _rng.uniform(0, 600),
            })


def _append_message(direction: str, msg_type: str, user_name: str,
                    channel: str, data: dict, record_id: str = "") -> dict:
    global _seq
    with _lock:
        _seq += 1
        frame = {
            "idx": _seq,
            "seq": _seq,
            "time": _now_ts(),
            "ts": _now(),
            "direction": direction,
            "type": msg_type,
            "channel": channel,
            "user_name": user_name,
            "conversation_id": f"conv_{uuid.uuid4().hex[:6]}",
            "record_id": record_id or uuid.uuid4().hex[:12],
            "content": data,
            "raw": json.dumps({"type": msg_type, "data": data}, ensure_ascii=False),
        }
        _messages.append(frame)
        if len(_messages) > 500:
            del _messages[:200]
        return frame


def _sse_worker():
    """周期性产生演示消息帧（买家提问 + 客服回复），驱动嗅探页实时流。"""
    global _seq
    while True:
        time.sleep(_rng.uniform(2.5, 5.0))
        try:
            _ensure_conversations()
            with _lock:
                conv = _rng.choice(_conversations) if _conversations else None
            if not conv:
                continue
            # 买家提问
            question = _rng.choice(_QUESTIONS)
            _append_message("client_to_server", "customer-question",
                            conv["user_name"], conv["platform"],
                            {"content": question,
                             "product_id": conv["product_id"]})
            time.sleep(0.8)
            # 客服回复
            reply = _rng.choice(_REPLIES)
            transfer = question == "我要转人工客服"
            _append_message("server_to_client", "reply-message",
                            conv["agent"], conv["platform"],
                            {"msg_list": [{"record_id": uuid.uuid4().hex[:12],
                                           "type": "TEXT",
                                           "content": reply,
                                           "transfer_to_human": transfer}]})
        except Exception:  # noqa: BLE001
            logger.exception("SSE worker 异常")


def _seed_messages() -> None:
    """启动时预置一批历史演示消息帧，让嗅探页/消息页默认就有数据。"""
    with _lock:
        if _messages:
            return
        _ensure_conversations()
        for i in range(10):
            conv = _conversations[i % len(_conversations)]
            question = _QUESTIONS[i % len(_QUESTIONS)]
            reply = _REPLIES[i % len(_REPLIES)]
            ts_q = _now_ts() - (10 - i) * 18
            ts_r = ts_q + 1.5
            _append_message("client_to_server", "customer-question",
                            conv["user_name"], conv["platform"],
                            {"content": question, "product_id": conv["product_id"]})
            _messages[-1]["time"] = ts_q
            _messages[-1]["ts"] = datetime.fromtimestamp(ts_q).strftime("%Y-%m-%d %H:%M:%S")
            _append_message("server_to_client", "reply-message",
                            conv["agent"], conv["platform"],
                            {"msg_list": [{"record_id": uuid.uuid4().hex[:12],
                                           "type": "TEXT",
                                           "content": reply,
                                           "transfer_to_human": question == "我要转人工客服"}]})
            _messages[-1]["time"] = ts_r
            _messages[-1]["ts"] = datetime.fromtimestamp(ts_r).strftime("%Y-%m-%d %H:%M:%S")


def _ensure_sse_worker():
    # 简单幂等：用全局标记
    global _sse_started
    if not globals().get("_sse_started"):
        globals()["_sse_started"] = True
        _seed_messages()
        t = threading.Thread(target=_sse_worker, daemon=True)
        t.start()


# ---------------------------------------------------------------- 只读接口

@bp.route("/demo", methods=["GET"])
def demo():
    return jsonify({"module": "ui", "messages": len(_messages),
                    "conversations": len(_conversations)})


@bp.route("/messages", methods=["GET"])
def messages():
    """历史消息帧。Query: limit"""
    _seed_messages()  # 幂等：首次访问时预置演示历史，嗅探页默认有数据
    limit = request.args.get("limit", 200, type=int)
    with _lock:
        frames = _messages[-limit:]
    return jsonify(frames)


@bp.route("/events", methods=["GET"])
def events():
    """SSE 实时消息流（嗅探页实时模式）。"""
    _ensure_sse_worker()

    def generate():
        last = 0
        with _lock:
            last = _seq
        yield "retry: 3000\n\n"
        while True:
            with _lock:
                new = [m for m in _messages if m["seq"] > last]
                if new:
                    last = new[-1]["seq"]
            for m in new:
                payload = {
                    "direction": m["direction"],
                    "type": m["type"],
                    "channel": m["channel"],
                    "user_name": m["user_name"],
                    "conversation_id": m["conversation_id"],
                    "record_id": m["record_id"],
                    "time": m["time"],
                    "content": m["content"],
                    "raw": m["raw"],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(0.5)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no",
                             "Connection": "keep-alive"})


@bp.route("/phrases", methods=["GET"])
def phrases():
    """话术库。"""
    return jsonify(_phrases())


@bp.route("/random-phrase", methods=["GET"])
def random_phrase():
    """随机一条话术。"""
    pool = _phrases()
    if pool:
        p = _rng.choice(pool)
        return jsonify({"phrase": p})
    return jsonify({"phrase": {"q": "演示", "a": "这是演示话术"}})


@bp.route("/assets", methods=["GET"])
def assets():
    """演示素材池。"""
    return jsonify({
        "images": [f"/static/demo_img_{i}.png" for i in range(1, 7)],
        "videos": [f"/static/demo_video_{i}.mp4" for i in range(1, 4)],
        "cards": {ch: [f"/static/demo_card_{i}.png" for i in range(1, 5)]
                  for ch in _CHANNELS},
    })


@bp.route("/active-conversations", methods=["GET"])
def active_conversations():
    """活跃会话列表。"""
    _ensure_conversations()
    with _lock:
        return jsonify(list(_conversations))


# ---------------------------------------------------------------- 发送类

def _send_response(data: dict, direction: str = "client_to_server",
                   msg_type: str = "reply-message", user: str = "演示客服A",
                   channel: str = "platform_a") -> dict:
    _ensure_sse_worker()
    _append_message(direction, msg_type, user, channel, data)
    return {"success": True, "message": "发送成功（演示）",
            "sent_to": 1, "time": _now()}


@bp.route("/send-text", methods=["POST"])
def send_text():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    channel = data.get("channel", "platform_a")
    user = data.get("user_name", "演示客服A")
    return jsonify(_send_response({"content": text}, msg_type="text-message",
                                  user=user, channel=channel))


@bp.route("/send-image", methods=["POST"])
def send_image():
    data = request.get_json(force=True, silent=True) or {}
    img = data.get("image_path", "/static/demo_img_1.png")
    return jsonify(_send_response({"image_path": img}, msg_type="image-message"))


@bp.route("/send-video", methods=["POST"])
def send_video():
    data = request.get_json(force=True, silent=True) or {}
    video = data.get("video_path", "/static/demo_video_1.mp4")
    return jsonify(_send_response({"video_path": video}, msg_type="video-message"))


@bp.route("/send-card", methods=["POST"])
def send_card():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("card_url", "/static/demo_card_1.png")
    return jsonify(_send_response({"card_url": url, "type": "card"},
                                  msg_type="card-message"))


@bp.route("/send-order", methods=["POST"])
def send_order():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("order_text", "演示订单：demo-sku-001 × 1")
    return jsonify(_send_response({"order_text": text, "type": "order"},
                                  msg_type="order-message"))


# ---------------------------------------------------------------- 批量自动发送

@bp.route("/send-batch", methods=["POST"])
def send_batch():
    """启动批量自动发送。Body: {ports, contact, total_rounds, message_type, ...}"""
    data = request.get_json(force=True, silent=True) or {}
    ports = data.get("ports") or []
    if not ports:
        return jsonify({"success": False, "error": "ports 不能为空"}), 400
    task_id = f"batch_{uuid.uuid4().hex[:8]}"

    rounds = int(data.get("total_rounds", 1) or 1)
    mtype = data.get("message_type", "text")
    interval = float(data.get("send_interval", 1) or 1)

    def _run():
        state = _batch_tasks[task_id]
        state["status"] = "running"
        total = len(ports) * rounds
        sent = 0
        failed = 0
        for r in range(rounds):
            for p in ports:
                if state.get("cancelled"):
                    state["status"] = "stopped"
                    break
                try:
                    _append_message("client_to_server", f"batch-{mtype}",
                                    f"port_{p}", "platform_a",
                                    {"port": p, "round": r + 1,
                                     "contact": data.get("contact", "")})
                    sent += 1
                except Exception:  # noqa: BLE001
                    failed += 1
                state["sent"] = sent
                state["failed"] = failed
                state["progress"] = int((sent + failed) / total * 100)
                time.sleep(max(0.1, interval * 0.1))
            if state.get("cancelled"):
                break
        if state["status"] == "running":
            state["status"] = "completed"
            state["progress"] = 100

    _batch_tasks[task_id] = {
        "task_id": task_id, "status": "pending", "sent": 0, "failed": 0,
        "progress": 0, "cancelled": False,
        "ports": ports, "rounds": rounds, "message_type": mtype,
    }
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"success": True, "task_id": task_id})


@bp.route("/send-batch/<task_id>/status", methods=["GET"])
def batch_status(task_id: str):
    state = _batch_tasks.get(task_id)
    if state is None:
        return jsonify({"error": "任务不存在"})
    return jsonify({k: v for k, v in state.items() if k != "cancelled"})


@bp.route("/send-batch/<task_id>/cancel", methods=["POST"])
def batch_cancel(task_id: str):
    state = _batch_tasks.get(task_id)
    if state is None:
        return jsonify({"success": False, "error": "任务不存在"}), 404
    state["cancelled"] = True
    return jsonify({"success": True, "message": "已请求停止"})


# ---------------------------------------------------------------- 注入

# 演示注入命令模板：
# - params  前端渲染输入框的字段（key = 报文占位符名）
# - defaults 预填值
# - data_template 报文 data 体模板，{xxx} 为占位符；未显式给出的会话字段
#   （user_name / nick_name / conversation_id / channel）由后端按所选会话自动带入
_CMD_TEMPLATES = [
    {
        "type": "reply_message",
        "name": "回复消息",
        "desc": "注入一条文本回复",
        "from_client": False,
        "params": {"text": "回复内容"},
        "defaults": {"text": "您好，感谢您的咨询（演示）"},
        "data_template": {
            "msg_list": [
                {"record_id": "{record_id}", "type": "TEXT",
                 "content": "{text}", "transfer_to_human": False},
            ],
            "user_name": "{user_name}",
            "conversation_id": "{conversation_id}",
            "channel": "{channel}",
        },
    },
    {
        "type": "transfer_message",
        "name": "转人工",
        "desc": "注入转人工指令",
        "from_client": False,
        "params": {"reason": "转接原因"},
        "defaults": {"reason": "用户要求转人工（演示）"},
        "data_template": {
            "msg_list": [
                {"record_id": "{record_id}", "type": "TEXT",
                 "content": "已为您转接人工客服", "transfer_to_human": True},
            ],
            "reason": "{reason}",
            "user_name": "{user_name}",
            "conversation_id": "{conversation_id}",
            "channel": "{channel}",
        },
    },
    {
        "type": "order_fetch",
        "name": "拉取订单",
        "desc": "注入订单拉取请求",
        "from_client": True,
        "params": {"order_id": "订单号", "query_scope": "查询范围"},
        "defaults": {"order_id": "demo-order-1001", "query_scope": "近7天"},
        "data_template": {
            "order_id": "{order_id}",
            "query_scope": "{query_scope}",
            "user_name": "{user_name}",
            "conversation_id": "{conversation_id}",
            "channel": "{channel}",
        },
    },
    {
        "type": "raw_message",
        "name": "原始报文",
        "desc": "注入自定义 JSON",
        "from_client": False,
        "params": {},
        "defaults": {},
        "data_template": None,
    },
]

# 需要活跃会话的命令（未选会话时不可注入）
_CMD_NEEDS_CONVERSATION = {"reply_message", "transfer_message", "order_fetch"}


@bp.route("/inject-commands", methods=["GET"])
def inject_commands():
    """注入命令模板列表（演示）。"""
    return jsonify(_CMD_TEMPLATES)


def _render_inject_template(tpl: dict, conv: dict | None,
                            params: dict) -> dict:
    """按命令模板 + 所选会话 + 用户参数渲染注入报文 data 体。

    占位符优先级：用户手填参数 > 会话字段（自动带入） > defaults 预填；
    request_id / record_id 等每次生成新 UUID。
    """
    values: dict[str, str] = {}
    for k, v in (conv or {}).items():
        if isinstance(v, str) and v:
            values[k] = v
    # 会话里平台字段名为 platform，报文占位符用 channel
    if conv and conv.get("platform"):
        values.setdefault("channel", conv["platform"])
    for k, v in (params or {}).items():
        if v:
            values[k] = str(v)
    values["record_id"] = uuid.uuid4().hex[:12]

    def _fill(node):
        if isinstance(node, str):
            return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), node)
        if isinstance(node, dict):
            return {k: _fill(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_fill(x) for x in node]
        return node

    return _fill(json.loads(json.dumps(tpl["data_template"])))


@bp.route("/quick-inject", methods=["POST"])
def quick_inject():
    """快速注入（演示）：按命令模板 + 所选会话组装报文。

    Body: {command_type, user_name, nick_name, conversation_id, platform,
           params: {...}, flow_id, wait, dry_run}
    返回: {success, injected_to, message: {type, request_id, task_id, priority, data}}
    """
    data = request.get_json(force=True, silent=True) or {}
    cmd_type = data.get("command_type", "reply_message")
    tpl = next((t for t in _CMD_TEMPLATES if t["type"] == cmd_type), None)
    if tpl is None or tpl.get("data_template") is None:
        return jsonify({"success": False, "error": f"命令模板不存在: {cmd_type}"}), 400

    # 按 conversation_id 定位所选会话，自动带入 user_name / conversation_id / channel
    conv = None
    cid = data.get("conversation_id") or ""
    if cid:
        with _lock:
            conv = next((c for c in _conversations if c["conversation_id"] == cid), None)
    if tpl["type"] in _CMD_NEEDS_CONVERSATION and conv is None:
        return jsonify({"success": False, "error": "请先选择一个活跃会话"}), 400

    rendered = _render_inject_template(
        tpl, conv, data.get("params") or {})
    message = {
        "type": tpl["type"],
        "request_id": uuid.uuid4().hex,
        "task_id": uuid.uuid4().hex,
        "priority": 2,
        "data": rendered,
    }

    dry_run = data.get("dry_run", False)
    if not dry_run:
        _ensure_sse_worker()
        direction = "client_to_server" if tpl.get("from_client") else "server_to_client"
        user = conv["user_name"] if conv else "演示买家小王"
        channel = conv["platform"] if conv else "platform_a"
        _append_message(direction, tpl["type"], user, channel, rendered)

    return jsonify({"success": True, "injected_to": 1,
                    "dry_run": bool(dry_run), "message": message})


@bp.route("/inject", methods=["POST"])
def inject():
    """消息注入（演示）。"""
    data = request.get_json(force=True, silent=True) or {}
    content = data.get("content", {})
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            content = {"content": content}
    _ensure_sse_worker()
    _append_message("server_to_client", "injected-message", "演示客服A",
                    data.get("channel", "platform_a"), content)
    return jsonify({"success": True, "injected_to": 1})


# ---------------------------------------------------------------- UI 操作（演示）

_ACTIONS = [
    {"name": "click_button", "desc": "点击按钮", "params": {"x": 0, "y": 0},
     "defaults": {"x": 100, "y": 200}},
    {"name": "type_text", "desc": "输入文本", "params": {"text": "", "x": 0, "y": 0},
     "defaults": {"text": "演示文本", "x": 100, "y": 200}},
    {"name": "screenshot", "desc": "截屏", "params": {}, "defaults": {}},
    {"name": "start_test", "desc": "启动测试", "params": {"case": ""},
     "defaults": {"case": "cases/platform_a/"}}]


@bp.route("/actions", methods=["GET"])
def actions():
    return jsonify(_ACTIONS)


@bp.route("/execute", methods=["POST"])
def execute():
    """执行 UI 操作（演示）。"""
    data = request.get_json(force=True, silent=True) or {}
    action = data.get("action", "")
    _ensure_sse_worker()
    _append_message("client_to_server", "ui-action", "演示客服A", "platform_a",
                    {"action": action, "params": data.get("params", {})})
    return jsonify({"success": True, "message": f"{action} 执行完成（演示）",
                    "result": {"action": action, "ok": True}})
