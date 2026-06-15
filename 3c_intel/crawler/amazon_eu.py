"""
Amazon 欧洲（德国 / 英国）Best Sellers 采集器
=============================================
逻辑与日本站基本一致，因 Amazon 各站点 HTML 结构相同，复用同一套解析逻辑。
单独成文件是为了：
1. 站点 / 语言请求头不同（德语 / 英语）。
2. 便于后续按地区独立扩展类目或特殊处理。
"""

from typing import Dict, List

from bs4 import BeautifulSoup

from config import AMAZON_EU_SOURCES, TOP_N_PER_SOURCE
from utils import cache
from utils.logger import get_logger

from .base import build_product, http_get

logger = get_logger("crawler.amazon_eu")


def _domain_of(url: str) -> str:
    """从 URL 中取出站点域名，用于补全相对链接。"""
    # https://www.amazon.de/gp/... -> https://www.amazon.de
    parts = url.split("/")
    return "/".join(parts[:3]) if len(parts) >= 3 else url


def _parse_bestseller_html(html: str, source: Dict) -> List[Dict]:
    """解析欧洲站畅销榜 HTML（结构与日本站一致）。"""
    soup = BeautifulSoup(html, "lxml")
    products: List[Dict] = []
    domain = _domain_of(source["url"])

    cards = soup.select("div.zg-grid-general-faceout") or soup.select(
        "div[id^='gridItemRoot']"
    ) or soup.select("div.p13n-sc-uncoverable-faceout")

    for idx, card in enumerate(cards, start=1):
        if idx > TOP_N_PER_SOURCE:
            break

        name_node = (
            card.select_one("div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1")
            or card.select_one("span.a-size-base-plus")
            or card.select_one("div.p13n-sc-truncate")
            or card.select_one("img")
        )
        if name_node is None:
            continue
        name = (
            name_node.get_text(strip=True)
            if name_node.name != "img"
            else name_node.get("alt", "")
        )

        link_node = card.select_one("a.a-link-normal[href]")
        link = ""
        if link_node:
            href = link_node.get("href", "")
            link = href if href.startswith("http") else f"{domain}{href}"

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


def crawl_amazon_eu() -> List[Dict]:
    """抓取所有配置的 Amazon 欧洲榜单（德国 / 英国）。"""
    results: List[Dict] = []

    for source in AMAZON_EU_SOURCES:
        cache_key = f"amazon_eu::{source['url']}"
        cached = cache.get(cache_key)
        if cached:
            results.extend(cached)
            continue

        # 德国站用德语请求头，英国站用英语
        lang = "de-DE,de;q=0.9" if "amazon.de" in source["url"] else "en-GB,en;q=0.9"
        resp = http_get(source["url"], headers={"Accept-Language": lang})
        if resp is None:
            logger.error("Amazon EU 抓取失败: %s", source["url"])
            continue

        items = _parse_bestseller_html(resp.text, source)
        if not items:
            logger.warning(
                "Amazon EU 未解析到商品（页面结构可能变动或被反爬）: %s",
                source["url"],
            )
        else:
            cache.set(cache_key, items)
        results.extend(items)

    return results
