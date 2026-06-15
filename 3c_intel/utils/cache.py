"""
本地缓存工具
============
基于文件的简单缓存，用于避免短时间内重复抓取同一数据源。

设计：每个 key 对应一个 JSON 文件，文件内记录写入时间戳与数据本体。
读取时若未过期（默认 6 小时）则直接返回缓存，否则视为失效。
"""

import hashlib
import json
import time
from typing import Any, Optional

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("cache")

CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

DEFAULT_TTL = 6 * 3600  # 默认缓存有效期 6 小时


def _key_to_path(key: str):
    """将任意 key 哈希为安全的文件名。"""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def get(key: str, ttl: int = DEFAULT_TTL) -> Optional[Any]:
    """读取缓存；命中且未过期返回数据，否则返回 None。"""
    path = _key_to_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if time.time() - payload.get("ts", 0) > ttl:
            logger.info("缓存已过期: %s", key)
            return None
        logger.info("命中缓存: %s", key)
        return payload.get("data")
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("读取缓存失败 %s: %s", key, exc)
        return None


def set(key: str, data: Any) -> None:
    """写入缓存。"""
    path = _key_to_path(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "data": data}, f, ensure_ascii=False)
        logger.info("写入缓存: %s", key)
    except OSError as exc:
        logger.warning("写入缓存失败 %s: %s", key, exc)
