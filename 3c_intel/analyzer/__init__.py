"""分析模块：爆品评分 + AI 简报生成。"""

from .scorer import score_products, top_n
from .ai_summary import generate_summary

__all__ = ["score_products", "top_n", "generate_summary"]
