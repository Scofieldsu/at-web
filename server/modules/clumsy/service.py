"""弱网进程管理服务（演示版）。

与真实实现的差异：不启动真实弱网工具进程、不依赖管理员权限与驱动，
"运行中" 为内存模拟状态（含 PID/时长），用于演示弱网配置下发与状态查询链路。
"""
from __future__ import annotations

import random
import threading
import time

from core.logging_config import get_logger
from server.runtime import project_root

from .models import ClumsyConfig, ClumsyStatus
from .presets import get_preset

logger = get_logger(__name__)


def _demo_exe() -> Path:
    """演示 exe 路径（假路径，不存在也不影响演示）。

    惰性求值：runtime.init() 在 create_app 时才执行，模块导入期不可用。
    """
    return project_root() / "tools" / "weaknet" / "weaknet.exe"


class ClumsyService:
    """弱网管理服务（单例）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pid: int | None = None
        self._config: ClumsyConfig | None = None
        self._start_time: float | None = None
        # 模拟 PID 起始值，避免每次相同
        self._pid_seq = random.randint(3000, 9000)

    # ---------------------------------------------------------------- 启停

    def start(self, config: ClumsyConfig | str) -> dict:
        """启动弱网（预设名或配置对象）。"""
        if isinstance(config, str):
            preset = get_preset(config)
            if not preset:
                return {"success": False, "message": f"预设配置 '{config}' 不存在"}
            config = preset

        with self._lock:
            if self.is_running():
                return {"success": False,
                        "message": f"弱网已在运行中 (PID={self._pid})，请先停止"}

            self._pid_seq += random.randint(7, 137)
            self._pid = self._pid_seq
            self._config = config
            self._start_time = time.time()

        logger.info("弱网启动（演示）: %s - %s", config.preset_name or "自定义",
                    config.summary())
        return {
            "success": True,
            "pid": self._pid,
            "message": (f"弱网已启动（演示）：{config.preset_name or '自定义配置'}"
                        f" - {config.summary()}"),
            "config": config.to_dict(),
        }

    def stop(self) -> dict:
        """停止弱网。"""
        with self._lock:
            if not self.is_running():
                return {"success": False, "message": "弱网未运行"}
            self._pid = None
            self._config = None
            self._start_time = None
        logger.info("弱网停止（演示）")
        return {"success": True, "message": "弱网已停止（演示）"}

    # ---------------------------------------------------------------- 状态

    def is_running(self) -> bool:
        with self._lock:
            return self._pid is not None

    def status(self) -> ClumsyStatus:
        with self._lock:
            running = self._pid is not None
            elapsed = int(time.time() - self._start_time) if (
                running and self._start_time) else 0
            summary = self._config.summary() if (running and self._config) else ""
            return ClumsyStatus(
                running=running,
                installed=True,
                exe_path=str(_demo_exe()),
                pid=self._pid if running else None,
                config=self._config,
                start_time=self._start_time,
                elapsed_seconds=elapsed,
                summary=summary,
            )

    def validate_installation(self) -> dict:
        """安装状态检查（演示：恒为已安装）。"""
        return {
            "installed": True,
            "path": str(_demo_exe()),
            "version": "demo-1.0",
            "message": "弱网工具已就绪（演示环境：不实际影响流量）",
        }


_service_instance: ClumsyService | None = None
_service_lock = threading.Lock()


def get_service() -> ClumsyService:
    """获取全局单例服务。"""
    global _service_instance
    with _service_lock:
        if _service_instance is None:
            _service_instance = ClumsyService()
        return _service_instance
