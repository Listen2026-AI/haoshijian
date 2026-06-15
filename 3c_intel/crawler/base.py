"""
采集基础工具
============
封装带重试、超时、限速的 HTTP GET / POST 请求，供各采集器复用。
"""

import time
from datetime import datetime
from typing import Optional

import requests

from config import (
    DEFAULT_HEADERS,
    REQUEST_DELAY,
    REQUEST_RETRY,
    REQUEST_TIMEOUT,
)
from utils.logger import get_logger

logger = get_logger("crawler.base")


def now_str() -> str:
    """统一的抓取时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def http_get(
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
) -> Optional[requests.Response]:
    """带重试与限速的 GET 请求；全部失败返回 None。"""
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}

    for attempt in range(1, REQUEST_RETRY + 1):
        try:
            resp = requests.get(
                url,
                headers=merged_headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                time.sleep(REQUEST_DELAY)  # 礼貌性限速
                return resp
            logger.warning(
                "GET %s 返回状态码 %s（第 %d 次）",
                url, resp.status_code, attempt,
            )
        except requests.RequestException as exc:
            logger.warning("GET %s 异常（第 %d 次）: %s", url, attempt, exc)

        # 指数退避
        time.sleep(min(2 ** attempt, 16))

    logger.error("GET %s 最终失败，已重试 %d 次", url, REQUEST_RETRY)
    return None


def http_post(
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    data: Optional[dict] = None,
    json_body: Optional[dict] = None,
) -> Optional[requests.Response]:
    """带重试与限速的 POST 请求；全部失败返回 None。"""
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}

    for attempt in range(1, REQUEST_RETRY + 1):
        try:
            resp = requests.post(
                url,
                headers=merged_headers,
                params=params,
                data=data,
                json=json_body,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                time.sleep(REQUEST_DELAY)
                return resp
            logger.warning(
                "POST %s 返回状态码 %s（第 %d 次）",
                url, resp.status_code, attempt,
            )
        except requests.RequestException as exc:
            logger.warning("POST %s 异常（第 %d 次）: %s", url, attempt, exc)

        time.sleep(min(2 ** attempt, 16))

    logger.error("POST %s 最终失败，已重试 %d 次", url, REQUEST_RETRY)
    return None


def build_product(
    name: str,
    price: str,
    rank: int,
    link: str,
    platform: str,
    country: str,
    category: str = "",
) -> dict:
    """构造统一结构的商品字典。"""
    return {
        "name": (name or "").strip(),
        "price": (price or "").strip(),
        "rank": rank,
        "link": (link or "").strip(),
        "platform": platform,
        "country": country,
        "category": category,
        "crawl_time": now_str(),
    }
