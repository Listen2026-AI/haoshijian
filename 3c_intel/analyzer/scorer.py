"""
爆品评分算法
============
score = 排名权重 + 多平台出现加分 + 关键词命中加分

- 排名权重：排名越靠前分越高。公式 max(0, RANK_BASE_SCORE - (rank-1)*step)，
  其中 step 让排名线性衰减。
- 多平台加分：商品在多个平台/地区榜单出现，说明全球性热度高。
- 关键词加分：命中“新品/Pro/AI”等关键词，代表新品 / 高端 / 智能趋势。
"""

from typing import Dict, List

from config import (
    KEYWORD_SCORES,
    MULTI_SOURCE_BONUS,
    RANK_BASE_SCORE,
    TOP_N_PER_SOURCE,
)
from utils.logger import get_logger

logger = get_logger("scorer")


def _rank_score(rank: int) -> float:
    """排名权重：第 1 名得满分，线性递减到榜尾。"""
    step = RANK_BASE_SCORE / max(TOP_N_PER_SOURCE, 1)
    return max(0.0, RANK_BASE_SCORE - (rank - 1) * step)


def _keyword_score(name: str) -> (float, List[str]):
    """关键词命中加分，返回 (加分, 命中的关键词列表)。"""
    name_lower = (name or "").lower()
    total = 0.0
    hits: List[str] = []
    for kw, sc in KEYWORD_SCORES.items():
        if kw.lower() in name_lower:
            total += sc
            hits.append(kw)
    return total, hits


def _multi_source_score(source_count: int) -> float:
    """多平台出现加分：每多出现一个来源加固定分。"""
    return max(0, source_count - 1) * MULTI_SOURCE_BONUS


def score_products(products: List[Dict]) -> List[Dict]:
    """
    为每个商品计算 score，并写回字段：
      - rank_score / multi_score / keyword_score / score
      - keyword_hits
    返回按 score 降序排序后的列表。
    """
    scored: List[Dict] = []

    for p in products:
        rank_sc = _rank_score(p.get("rank", TOP_N_PER_SOURCE))
        multi_sc = _multi_source_score(p.get("source_count", 1))
        kw_sc, kw_hits = _keyword_score(p.get("name", ""))

        total = round(rank_sc + multi_sc + kw_sc, 2)

        item = dict(p)
        item.update(
            {
                "rank_score": round(rank_sc, 2),
                "multi_score": multi_sc,
                "keyword_score": kw_sc,
                "keyword_hits": kw_hits,
                "score": total,
            }
        )
        scored.append(item)

    scored.sort(key=lambda x: x["score"], reverse=True)
    logger.info("已为 %d 个商品评分", len(scored))
    return scored


def top_n(scored_products: List[Dict], n: int) -> List[Dict]:
    """取评分最高的前 N 个。"""
    return scored_products[:n]
