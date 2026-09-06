"""AT Web Flask 应用工厂。

- /api/* 统一 session 鉴权（登录接口本身除外）
- 模块自动发现注册（server/modules/*）
- 托管前端构建产物 frontend/dist（hash 路由 SPA 回退）
- 占位外链页 /ext/*（演示用，替代源工程内网外链）
"""
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, render_template_string

from core.config import AppConfig, load_platforms
from core.logging_config import setup_logging, get_logger

from .modules import register_all
from .modules.auth import is_authenticated

logger = get_logger(__name__)

_EXT_PAGES = {
    "vm-console": {
        "title": "VM 控制台",
        "desc": "演示占位页 — 源系统中此处链接到内网虚拟机管理控制台。",
    },
    "minio": {
        "title": "对象存储（MinIO）",
        "desc": "演示占位页 — 源系统中此处链接到内网对象存储控制台。",
    },
}

_EXT_PAGE_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
  body { margin: 0; font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
         background: #f8f9fa; color: #1c2024; }
  .wrap { max-width: 640px; margin: 120px auto; background: #fff; border: 1px solid #e5e5e5;
          border-radius: 4px; padding: 32px; }
  .tag { display: inline-block; background: rgba(99,102,241,0.12); color: #6366f1;
         border: 1px solid rgba(99,102,241,0.25); border-radius: 4px;
         font-size: 12px; padding: 2px 8px; margin-bottom: 12px; }
  h1 { font-size: 18px; margin: 0 0 8px; }
  p { font-size: 13px; color: #60646c; line-height: 1.7; }
  a { color: #6366f1; text-decoration: none; font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">
  <span class="tag">DEMO</span>
  <h1>{{ title }}</h1>
  <p>{{ desc }}</p>
  <p><a href="javascript:history.back()">← 返回控制台</a></p>
</div>
</body>
</html>
"""


def create_app(app_config: AppConfig | None = None) -> Flask:
    """创建 Flask 应用。"""
    if app_config is None:
        app_config = AppConfig.load_from_project(Path(__file__).parent.parent)

    project_root = app_config.paths.project_root

    from datetime import datetime as _dt
    setup_logging(
        log_level=app_config.log.level,
        log_file=app_config.log.file,
        log_dir=str(project_root / app_config.log.dir),
        max_bytes=app_config.log.max_bytes,
        backup_count=app_config.log.backup_count,
    )
    logger.info("Initializing AT Web Flask application with unified config")

    # 运行时上下文（后台线程统一从此读取，不依赖请求上下文）
    from . import runtime
    runtime.init(project_root, app_config.current_env, load_platforms(app_config.paths.config_dir))

    # 执行引擎初始化（演示引擎）
    from .engine import init_engine
    init_engine(app_config.engine)

    # 演示数据填充（幂等：首次启动生效）
    from .seed import seed_all
    platforms = runtime.platforms()
    seed_all(project_root, platforms)

    app = Flask(__name__)
    app.secret_key = os.getenv("AT_WEB_SECRET_KEY", "at-web-demo-secret-change-me")

    app.config.from_mapping(
        SERVER_PORT=app_config.server.port,
        DEBUG=app_config.server.debug,
        PROJECT_ROOT=str(project_root),
        LOG_DIR=str(app_config.log.dir),
        LOG_FILE=app_config.log.file,
        PLATFORMS=load_platforms(app_config.paths.config_dir),
        ENGINE=app_config.engine,
        WEB_USERS=list(app_config.web_users.users),
        CURRENT_ENV=app_config.current_env,
    )

    @app.before_request
    def _auth_guard():
        path = request.path
        if not path.startswith("/api/"):
            return
        if path == "/api/auth/login":
            return
        if not is_authenticated():
            return jsonify({"error": "unauthorized"}), 401

    register_all(app)

    # ---- 任务历史冷启动回填（幂等）----
    from .modules.tasks import _warm_history
    _warm_history(str(project_root))

    # ---- 定时任务调度线程 ----
    from .modules import schedules as _schedules
    _schedules.start()

    # ---- Mock 中控服务默认启动（演示：消息流/连接默认有数据）----
    from .modules import mock_ws as _mock_ws
    _mock_ws.auto_start()

    # ---- 占位外链页（演示）----
    for key, info in _EXT_PAGES.items():
        endpoint = f"ext_{key}"

        def _ext_view(_title=info["title"], _desc=info["desc"]):
            return render_template_string(_EXT_PAGE_HTML, title=_title, desc=_desc)

        app.add_url_rule(f"/ext/{key}", endpoint=endpoint, view_func=_ext_view)

    @app.route("/health")
    def health():
        return {"status": "ok", "modules": [r.name for r in app.blueprints.values()]}

    # ---- 托管 Vue SPA 构建产物（frontend/dist）----
    dist_dir = app_config.paths.web_dist

    @app.get("/")
    @app.get("/<path:path>")
    def spa(path: str = ""):
        full = dist_dir / path
        if path and full.is_file():
            return send_from_directory(str(dist_dir), path)
        index = dist_dir / "index.html"
        if index.is_file():
            return send_from_directory(str(dist_dir), "index.html")
        return ("前端尚未构建：请在 frontend/ 下执行 pnpm install && pnpm build", 200)

    logger.info("Flask app created, listening on %s:%s", app_config.server.host, app_config.server.port)
    return app
