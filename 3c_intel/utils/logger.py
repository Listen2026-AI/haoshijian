"""
日志工具
========
统一的日志配置：同时输出到控制台和文件（按天滚动）。
其他模块通过 `from utils.logger import get_logger` 获取 logger。
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from config import LOG_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_initialized = False


def _init_root_logger() -> None:
    """初始化根日志器（只执行一次）。"""
    global _initialized
    if _initialized:
        return

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 控制台输出
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(console)

    # 文件输出，按天切分，保留 14 天
    file_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "app.log",
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取带统一配置的 logger。"""
    _init_root_logger()
    return logging.getLogger(name)
