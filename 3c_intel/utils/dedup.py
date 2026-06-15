"""
商品去重工具
============
不同榜单/平台可能出现“同一款商品”，需要识别并合并。

去重策略：
1. 对商品名做归一化（小写、去空格、去常见符号）。
2. 取归一化后的前 N 个字符做指纹（避免长名称尾部差异导致漏判）。
3. 同一指纹的商品视为重复，合并时记录其出现过的来源，用于“多平台加分”。
"""

import re
from typing import Dict, List

from utils.logger import get_logger

logger = get_logger("dedup")

_NORMALIZE_RE = re.compile(r"[\s\-_/|,，。、（）()\[\]【】!！?？:：]+")


def _normalize(name: str) -> str:
    """商品名归一化，用于生成去重指纹。"""
    name = (name or "").lower()
    name = _NORMALIZE_RE.sub("", name)
    return name[:40]  # 取前 40 个字符作为指纹


def dedup_products(products: List[Dict]) -> List[Dict]:
    """
    对商品列表去重。
    返回去重后的列表，每个商品额外带：
      - sources: 出现过的 (平台, 国家) 集合（list 形式，便于序列化）
      - source_count: 出现来源数量（用于多平台加分）
    """
    merged: Dict[str, Dict] = {}

    for p in products:
        fp = _normalize(p.get("name", ""))
        if not fp:
            continue

        source_tag = f"{p.get('platform', '')}-{p.get('country', '')}"

        if fp in merged:
            # 已存在：合并来源，保留排名更靠前（数值更小）的记录
            existing = merged[fp]
            existing.setdefault("sources", [])
            if source_tag not in existing["sources"]:
                existing["sources"].append(source_tag)
            # 排名取更靠前的（更小）
            if p.get("rank", 9999) < existing.get("rank", 9999):
                # 保留更靠前的展示信息，但保留来源集合
                sources = existing["sources"]
                merged[fp] = {**p, "sources": sources}
        else:
            new_item = dict(p)
            new_item["sources"] = [source_tag]
            merged[fp] = new_item

    result = []
    for item in merged.values():
        item["source_count"] = len(item.get("sources", []))
        result.append(item)

    logger.info("去重前 %d 条，去重后 %d 条", len(products), len(result))
    return result
