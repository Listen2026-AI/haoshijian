"""
京东热卖榜采集器
================
京东官方榜单页（rank.jd.com）对爬虫强反爬（需要登录态 / 风控 cookie），
直接用 requests 抓取成功率低。

因此采用“可替代榜单”策略：
- 抓取京东 PC 端搜索页（search.jd.com），按指定关键词 + 销量排序，
  取前 N 个商品作为“热卖榜”近似值。
- 搜索结果页结构相对稳定，且无需登录即可访问部分内容。

技术说明：
- 优先使用 requests + BeautifulSoup。
- 搜索页价格部分由 JS 异步加载，HTML 首屏可能不含价格，
  此时价格字段留空（不影响榜单与评分主流程）。
- 若需要 100% 拿到价格 / 完整榜单，可改用 Playwright 渲染（默认不启用）。
"""

from typing import Dict, List
from urllib.parse import quote

from bs4 import BeautifulSoup

from config import JD_SOURCES, TOP_N_PER_SOURCE
from utils import cache
from utils.logger import get_logger

from .base import build_product, http_get

logger = get_logger("crawler.jd")

# 京东 PC 搜索页：psort=3 表示按销量排序
JD_SEARCH_URL = "https://search.jd.com/Search?keyword={kw}&enc=utf-8&psort=3"


def _parse_search_html(html: str, source: Dict) -> List[Dict]:
    """解析京东搜索结果页，提取商品。"""
    soup = BeautifulSoup(html, "lxml")
    products: List[Dict] = []

    # 商品列表项：li.gl-item
    items = soup.select("li.gl-item")

    for idx, li in enumerate(items, start=1):
        if idx > TOP_N_PER_SOURCE:
            break

        # 商品名
        name_node = li.select_one("div.p-name em") or li.select_one("div.p-name a")
        name = name_node.get_text(strip=True) if name_node else ""

        # 链接
        link_node = li.select_one("div.p-name a[href]") or li.select_one("a[href]")
        link = ""
        if link_node:
            href = link_node.get("href", "")
            link = ("https:" + href) if href.startswith("//") else href

        # 价格（可能为空，JS 异步加载）
        price_node = li.select_one("div.p-price i") or li.select_one("div.p-price strong i")
        price = ("¥" + price_node.get_text(strip=True)) if price_node else ""

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


def crawl_jd() -> List[Dict]:
    """抓取京东热卖（按销量排序的搜索结果作为替代榜单）。"""
    results: List[Dict] = []

    for source in JD_SOURCES:
        keyword = source.get("search_keyword", "3C数码")
        url = JD_SEARCH_URL.format(kw=quote(keyword))

        cache_key = f"jd::{keyword}"
        cached = cache.get(cache_key)
        if cached:
            results.extend(cached)
            continue

        # 京东需要带 Referer 与中文 cookie 习惯，附加部分请求头
        resp = http_get(
            url,
            headers={
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://www.jd.com/",
            },
        )
        if resp is None:
            logger.error("京东抓取失败: %s", url)
            continue

        # 京东可能返回 gbk 编码
        resp.encoding = resp.apparent_encoding or "utf-8"
        items = _parse_search_html(resp.text, source)
        if not items:
            logger.warning("京东未解析到商品（可能被风控或结构变动）: %s", url)
        else:
            cache.set(cache_key, items)
        results.extend(items)

    return results
