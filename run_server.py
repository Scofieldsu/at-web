"""AT Web 管理后台启动入口（一键启动 Flask 服务，托管前端 dist）。"""
from pathlib import Path

from core.config import AppConfig
from server import create_app


def main():
    project_root = Path(__file__).parent
    app_config = AppConfig.load_from_project(project_root)

    app = create_app(app_config)

    print(f"Starting AT Web server on {app_config.server.host}:{app_config.server.port}")
    print(f"Project root: {project_root}")
    print("---")

    app.run(
        host=app_config.server.host,
        port=app_config.server.port,
        debug=app_config.server.debug,
    )


if __name__ == "__main__":
    main()
