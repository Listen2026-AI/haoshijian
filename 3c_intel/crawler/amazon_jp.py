"""
Amazon 日本 Best Sellers 采集器
================================
抓取 amazon.co.jp 指定类目的畅销榜前 N 名。

技术说明：
- 优先使用 requests + BeautifulSoup 直接解析 HTML。
- Amazon 的畅销榜 HTML 结构经常变动，且部分内容由前端渲染，
  因此采用“多套选择器兜底”的策略，尽量提高解析成功率。
- 若后续发现该页大量内容必须 JS 渲染才能拿到（requests 拿到的是空壳），
  可改用 Playwright（见 crawler/README 注释），但默认不引入以保持轻量。
"""

from typing import Dict, List

from bs4 import BeautifulSoup

from config import AMAZON_JP_SOURCES, TOP_N_PER_SOURCE
from utils import cache
from utils.logger import get_logger

from .base import build_product, http_get

logger = get_logger("crawler.amazon_jp")


def _parse_bestseller_html(html: str, source: Dict) -> List[Dict]:
    """从畅销榜 HTML 中解析商品列表。"""
    soup = BeautifulSoup(html, "lxml")
    products: List[Dict] = []

    # Amazon 畅销榜每个商品通常在带 data-asin 或 class 含 zg-grid 的卡片中
    cards = soup.select("div.zg-grid-general-faceout") or soup.select(
        "div[id^='gridItemRoot']"
    ) or soup.select("div.p13n-sc-uncoverable-faceout")

    for idx, card in enumerate(cards, start=1):
        if idx > TOP_N_PER_SOURCE:
            break

        # 商品名：尝试多种节点
        name_node = (
            card.select_one("div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1")
            or card.select_one("span.a-size-base-plus")
            or card.select_one("div.p13n-sc-truncate")
            or card.select_one("img")
        )
        if name_node is None:
            continue
        name = name_node.get_text(strip=True) if name_node.name != "img" else name_node.get("alt", "")

        # 链接
        link_node = card.select_one("a.a-link-normal[href]")
        link = ""
        if link_node:
            href = link_node.get("href", "")
            link = href if href.startswith("http") else f"https://www.amazon.co.jp{href}"

        # 价格
        price_node = card.select_one("span.a-price span.a-offscreen") or card.select_one(
            "span._cDEzb_p13n-sc-price_3mJ9Z"
        )
        price = price_node.get_text(strip=True) if price_node else ""

        if not name:
            continue

        products.append(
            build_product(
                name=name,
                price=price,
                rank=idx,
                link=link,
                platform=source["platform"],
                country=source["country"],
                category=source["category"],
            )
        )

    return products


def crawl_amazon_jp() -> List[Dict]:
    """抓取所有配置的 Amazon 日本榜单。"""
    results: List[Dict] = []

    for source in AMAZON_JP_SOURCES:
        cache_key = f"amazon_jp::{source['url']}"
        cached = cache.get(cache_key)
        if cached:
            results.extend(cached)
            continue

        resp = http_get(source["url"], headers={"Accept-Language": "ja-JP,ja;q=0.9"})
        if resp is None:
            logger.error("Amazon JP 抓取失败: %s", source["url"])
            continue

        items = _parse_bestseller_html(resp.text, source)
        if not items:
            logger.warning(
                "Amazon JP 未解析到商品（页面结构可能变动或被反爬）: %s",
                source["url"],
            )
        else:
            cache.set(cache_key, items)
        results.extend(items)

    return results
