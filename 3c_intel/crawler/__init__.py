"""
采集模块
========
对外暴露统一入口 `collect_all()`，聚合所有数据源的抓取结果。
"""

from typing import Dict, List

from utils.logger import get_logger

from .amazon_jp import crawl_amazon_jp
from .amazon_eu import crawl_amazon_eu
from .jd import crawl_jd

logger = get_logger("crawler")


def collect_all() -> List[Dict]:
    """
    依次执行所有数据源采集，任意单源失败不影响其他源。
    返回所有商品的扁平列表。
    """
    all_products: List[Dict] = []

    for name, func in (
        ("Amazon 日本", crawl_amazon_jp),
        ("Amazon 欧洲", crawl_amazon_eu),
        ("京东", crawl_jd),
    ):
        try:
            items = func()
            logger.info("[%s] 抓取到 %d 条", name, len(items))
            all_products.extend(items)
        except Exception as exc:  # noqa: BLE001 单源异常隔离，保证整体不崩
            logger.error("[%s] 抓取失败: %s", name, exc, exc_info=True)

    logger.info("全部数据源合计抓取 %d 条", len(all_products))
    return all_products
