"""
定时调度器（Python schedule 方式）
==================================
每天在指定时间（默认 08:00）自动执行一次完整流程。

运行方式（需保持进程常驻）：
    python scheduler.py

时间由环境变量 SCHEDULE_TIME 控制（格式 HH:MM，默认 08:00）。

如果更倾向用系统级 cron（推荐用于服务器），见 README 的「部署定时任务」章节，
那种方式无需让本脚本常驻。
"""

import time

import schedule

from config import SCHEDULE_TIME
from main import run_once
from utils.logger import get_logger

logger = get_logger("scheduler")


def _job():
    """调度任务包装，捕获异常避免调度线程崩溃。"""
    try:
        run_once()
    except Exception as exc:  # noqa: BLE001
        logger.error("定时任务执行异常: %s", exc, exc_info=True)


def main():
    logger.info("调度器启动，每天 %s 执行一次。按 Ctrl+C 退出。", SCHEDULE_TIME)
    schedule.every().day.at(SCHEDULE_TIME).do(_job)

    while True:
        schedule.run_pending()
        time.sleep(30)  # 每 30 秒检查一次是否到点


if __name__ == "__main__":
    main()
