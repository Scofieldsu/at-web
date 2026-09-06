"""日志初始化 — 控制台 + 按日滚动文件（与源平台日志约定一致）。"""
from __future__ import annotations

import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

_lock = threading.Lock()
_initialized = False


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "app.log",
    log_dir: str = "var/logs",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    global _initialized
    with _lock:
        if _initialized:
            return
        root = logging.getLogger()
        root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)

        if log_file:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_path / log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(fmt)
            root.addHandler(file_handler)

        _initialized = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
