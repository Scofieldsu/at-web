"""AT Web Flask 应用工厂。

- /api/* 统一 session 鉴权（登录接口本身除外）
- 模块自动发现注册（server/modules/*）
- 托管前端构建产物 frontend/dist（hash 路由 SPA 回退）
- 外链演示页 /ext/*（JIRA 风格缺陷跟踪 + 文件存储，静态页替代源工程内网外链）
"""
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from core.config import AppConfig, load_platforms
from core.logging_config import setup_logging, get_logger

from .modules import register_all
from .modules.auth import is_authenticated

logger = get_logger(__name__)

# 外链演示页：静态整页（server/static/ext/*.html），参考 JIRA / 文件存储系统设计
_EXT_PAGES = {
    "defects": "defects.html",
    "files": "files.html",
}
_EXT_STATIC_DIR = Path(__file__).parent / "static" / "ext"


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

    # ---- 外链演示页（/ext/* → server/static/ext/*.html）----
    for key, filename in _EXT_PAGES.items():
        app.add_url_rule(
            f"/ext/{key}",
            endpoint=f"ext_{key}",
            view_func=lambda f=filename: send_from_directory(str(_EXT_STATIC_DIR), f),
        )

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
