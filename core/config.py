"""统一的配置管理模块 — 支持 YAML、环境变量多来源配置加载。

与源平台保持一致的加载约定：
    config/main/config.yaml 为唯一主配置，环境变量可按前缀覆盖。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Type, TypeVar

import yaml

T = TypeVar("T", bound="BaseConfig")


@dataclass
class BaseConfig:
    """配置基类，支持从 YAML、环境变量加载。"""

    @classmethod
    def from_yaml(cls: Type[T], yaml_path: str | Path) -> T:
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            return cls()
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def from_env(cls: Type[T], prefix: str = "") -> T:
        data = {}
        for f in fields(cls):
            env_key = f"{prefix}{f.name}".upper()
            env_value = os.environ.get(env_key)
            if env_value is not None:
                data[f.name] = cls._convert_type(env_value, f.type)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls: Type[T], data: dict[str, Any]) -> T:
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    @classmethod
    def _merge(cls: Type[T], base: T, override: T) -> T:
        base_dict = {f.name: getattr(base, f.name) for f in fields(cls)}
        override_dict = {f.name: getattr(override, f.name) for f in fields(cls)}
        default_dict = {f.name: f.default if f.default is not field else None for f in fields(cls)}
        for key, override_value in override_dict.items():
            if override_value != default_dict.get(key):
                base_dict[key] = override_value
        return cls(**base_dict)

    @staticmethod
    def _convert_type(value: str, target_type: type) -> Any:
        if target_type == bool:
            return value.lower() in ("1", "true", "yes", "on")
        if target_type == int:
            return int(value)
        if target_type == float:
            return float(value)
        return value


@dataclass
class LogConfig(BaseConfig):
    """日志配置。"""
    level: str = "INFO"
    file: str = "app.log"
    dir: str = "var/logs"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass
class ServerConfig(BaseConfig):
    """Web 服务配置。"""
    port: int = 6001
    host: str = "0.0.0.0"
    debug: bool = True


@dataclass
class WebUsersConfig(BaseConfig):
    """登录账号配置（配置式账号 + session cookie，支持多账号）。

    推荐列表格式（config.yaml 的 web_users 段）::

        web_users:
          - username: admin
            password: demo123
          - username: demo
            password: demo123

    兼容旧单账号格式（admin_user/admin_pass 两键），加载时归一化为列表。
    """
    users: list[dict] = field(default_factory=lambda: [
        {"username": "admin", "password": "demo123"},
        {"username": "demo", "password": "demo123"},
    ])

    @classmethod
    def _from_dict(cls: Type["WebUsersConfig"], d: Any) -> "WebUsersConfig":
        # 列表格式（推荐）
        if isinstance(d, list):
            users = [
                {"username": str(i.get("username", "")).strip(),
                 "password": str(i.get("password", ""))}
                for i in d if isinstance(i, dict) and str(i.get("username", "")).strip()
            ]
            return cls(users=users or list(cls._default_users()))
        # 单账号字典格式（兼容：username/password 或 admin_user/admin_pass）
        if isinstance(d, dict) and ("username" in d or "admin_user" in d):
            name = str(d.get("username") or d.get("admin_user") or "admin").strip()
            pwd = str(d.get("password") or d.get("admin_pass") or "demo123")
            return cls(users=[{"username": name, "password": pwd}])
        # 含 users 键的标准 dataclass 格式
        if isinstance(d, dict) and "users" in d:
            return cls(users=list(d["users"]))
        return cls(users=list(cls._default_users()))

    @staticmethod
    def _default_users() -> list[dict]:
        return [
            {"username": "admin", "password": "demo123"},
            {"username": "demo", "password": "demo123"},
        ]


@dataclass
class Platform(BaseConfig):
    """单个平台的定义。"""
    key: str = ""            # 唯一标识（platform_a）
    name: str = ""           # 展示名（平台A）
    port: int = 0            # 起始端口
    type: int = 0            # 前端 platform_type 数字编码
    install_dir: str = ""    # 被测代理安装目录（演示值）
    exe: str = ""            # 主程序文件名（演示值）
    window_title: str = ""   # 窗口标题（演示值）


@dataclass
class EngineConfig(BaseConfig):
    """执行引擎配置 — 演示引擎的模拟参数。"""
    kind: str = "demo"                    # demo=内置模拟引擎
    task_duration_min: float = 3.0        # 单任务最短时长（秒）
    task_duration_max: float = 8.0        # 单任务最长时长（秒）
    fail_rate: float = 0.15               # 任务失败概率（演示用）


@dataclass
class PathConfig(BaseConfig):
    """路径配置（项目文件和目录）。"""
    project_root: Path = field(default_factory=Path.cwd)
    config_dir: Path = field(default_factory=lambda: Path("config"))
    data_dir: Path = field(default_factory=lambda: Path("var/data"))
    results_dir: Path = field(default_factory=lambda: Path("var/results"))
    web_dist: Path = field(default_factory=lambda: Path("frontend/dist"))

    @classmethod
    def from_project_root(cls, root: Path) -> "PathConfig":
        return cls(
            project_root=root,
            config_dir=root / "config",
            data_dir=root / "var" / "data",
            results_dir=root / "var" / "results",
            web_dist=root / "frontend" / "dist",
        )


@dataclass
class AppConfig(BaseConfig):
    """应用全局配置。"""
    log: LogConfig = field(default_factory=LogConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    web_users: WebUsersConfig = field(default_factory=WebUsersConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    current_env: str = "dev"  # 当前环境 dev/prod（测试计划与账号按环境分组）

    @classmethod
    def load_from_project(cls, project_root: str | Path | None = None) -> "AppConfig":
        if project_root is None:
            project_root = Path.cwd()
        else:
            project_root = Path(project_root)

        config_file = project_root / "config" / "main" / "config.yaml"
        config_data = {}
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

        app_config = cls()
        if "log" in config_data:
            app_config.log = LogConfig._from_dict(config_data["log"])
        if "server" in config_data:
            app_config.server = ServerConfig._from_dict(config_data["server"])
        if "web_users" in config_data:
            app_config.web_users = WebUsersConfig._from_dict(config_data["web_users"])
        if "engine" in config_data:
            app_config.engine = EngineConfig._from_dict(config_data["engine"])
        if isinstance(config_data.get("current_env"), str):
            app_config.current_env = config_data["current_env"]

        # 环境选择器（与 rpa-test-automation 的 config/rpa/env.json 同构）：
        # 优先级 环境变量 AT_WEB_ENV > config/env.json 的 current > config.yaml current_env > dev
        app_config.current_env = resolve_current_env(project_root, app_config.current_env)

        # 环境变量覆盖
        # 注：web_users 不走 _merge（其 users 字段无标量默认值，merge 会用默认账号表
        # 覆盖文件配置）；多账号环境变量由 auth 模块直接读 AT_WEB_* 处理。
        app_config.log = LogConfig._merge(app_config.log, LogConfig.from_env("LOG_"))
        app_config.server = ServerConfig._merge(app_config.server, ServerConfig.from_env("SERVER_"))
        app_config.engine = EngineConfig._merge(app_config.engine, EngineConfig.from_env("ENGINE_"))

        app_config.paths = PathConfig.from_project_root(project_root)
        return app_config


ENV_JSON_RELPATH = Path("config") / "env.json"


def resolve_current_env(project_root: str | Path, fallback: str = "dev") -> str:
    """解析当前环境。

    优先级（与 rpa-test-automation 的 EnvLoader 一致，仅配置来源改为本项目）：
      1. 环境变量 AT_WEB_ENV
      2. config/env.json 的 current 字段
      3. fallback（config.yaml 的 current_env）
      4. dev
    """
    import json
    import os

    env_var = os.getenv("AT_WEB_ENV")
    if env_var:
        return env_var

    env_file = Path(project_root) / ENV_JSON_RELPATH
    try:
        if env_file.exists():
            data = json.loads(env_file.read_text(encoding="utf-8"))
            current = data.get("current")
            if isinstance(current, str) and current.strip():
                return current.strip()
    except (OSError, json.JSONDecodeError):
        pass
    return fallback or "dev"


def save_current_env(project_root: str | Path, env: str) -> None:
    """把当前环境写回 config/env.json 的 current 字段（保留注释键，缩进与 rpa 项目一致）。"""
    import json

    env_file = Path(project_root) / ENV_JSON_RELPATH
    data: dict[str, Any] = {}
    if env_file.exists():
        try:
            data = json.loads(env_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError):
            data = {}
    data["current"] = env
    env_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_platforms(config_root: Path) -> list[dict]:
    """读取 config/platforms/platforms.json，返回平台定义列表。

    平台概念完全配置驱动：新增/删除平台只改这个 JSON，无需动代码。
    """
    import json

    path = config_root / "platforms" / "platforms.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    platforms = []
    for key, cfg in data.items():
        if not isinstance(cfg, dict):
            continue
        platforms.append({
            "key": key,
            "name": cfg.get("name", key),
            "port": int(cfg.get("port", 0)),
            "type": int(cfg.get("type", len(platforms) + 1)),
            "install_dir": cfg.get("install_dir", ""),
            "exe": cfg.get("exe", ""),
            "window_title": cfg.get("window_title", ""),
            "buttons": cfg.get("buttons", []),
        })
    return platforms
