"""模块自动发现与注册。

每个子目录需要在 __init__.py 中定义 `bp` (Flask Blueprint)。
create_app() 调用 register_all() 自动扫描并注册所有模块。
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from flask import Flask

from core.logging_config import get_logger

logger = get_logger(__name__)


def register_all(app: Flask) -> None:
    package_dir = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if not module_info.ispkg:
            continue
        module = importlib.import_module(f".{module_info.name}", package=__package__)
        bp = getattr(module, "bp", None)
        if bp is not None:
            app.register_blueprint(bp)
            logger.info("注册模块: %s", module_info.name)
