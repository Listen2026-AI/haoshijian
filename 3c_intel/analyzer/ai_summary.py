"""
AI 分析总结
===========
调用 OpenAI API 生成每日中文简报（300-500 字）。
若未配置 OPENAI_API_KEY 或调用失败，自动降级为“本地模板总结”，
保证主流程（评分 + 推送）永远可用。

简报内容：
- 今日爆品 Top 5（带简要说明）
- 新出现的潜力产品
- 各地区趋势差异（中国 vs 日本 vs 欧洲）
- 值得关注的品类变化
"""

from collections import Counter
from typing import Dict, List, Optional

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from utils.logger import get_logger

logger = get_logger("ai_summary")


def _build_prompt(top_products: List[Dict]) -> str:
    """根据 Top 商品构造发给大模型的提示词。"""
    lines = ["以下是今日采集到的 3C 爆品榜单数据（已按爆品评分排序）：\n"]
    for i, p in enumerate(top_products, start=1):
        hits = "、".join(p.get("keyword_hits", [])) or "无"
        lines.append(
            f"{i}. {p.get('name', '')[:60]} | 平台:{p.get('platform')} | "
            f"地区:{p.get('country')} | 价格:{p.get('price') or '未知'} | "
            f"评分:{p.get('score')} | 命中关键词:{hits}"
        )

    data_block = "\n".join(lines)

    prompt = f"""你是一名资深的 3C 跨境电商情报分析师。请根据下面的爆品榜单数据，
撰写一份**简洁的中文每日简报**，要求 300-500 字，结构清晰，包含以下四部分：

1. 今日爆品 Top 5（每个一句话简要说明为什么火）
2. 新出现的潜力产品（点出 1-3 个值得关注的新品/上升品）
3. 各地区趋势差异（对比 中国 vs 日本 vs 欧洲 的偏好）
4. 值得关注的品类变化（指出品类层面的信号）

请直接输出简报正文，不要加任何前言或解释。

数据如下：
{data_block}
"""
    return prompt


def _local_fallback_summary(top_products: List[Dict]) -> str:
    """无 AI 时的本地模板总结，基于统计规则生成可读简报。"""
    if not top_products:
        return "今日未采集到有效爆品数据，请检查数据源或网络。"

    # 地区分布统计
    country_counter = Counter(p.get("country", "未知") for p in top_products)
    platform_counter = Counter(p.get("platform", "未知") for p in top_products)
    kw_counter: Counter = Counter()
    for p in top_products:
        kw_counter.update(p.get("keyword_hits", []))

    top5 = top_products[:5]
    top5_lines = []
    for i, p in enumerate(top5, start=1):
        reason = []
        if p.get("multi_score", 0) > 0:
            reason.append("多地区上榜")
        if p.get("keyword_hits"):
            reason.append("命中热点关键词:" + "、".join(p["keyword_hits"]))
        if p.get("rank", 99) <= 3:
            reason.append("榜单靠前")
        reason_str = "；".join(reason) or "综合热度较高"
        top5_lines.append(
            f"{i}. {p.get('name', '')[:40]}（{p.get('country')}/{p.get('platform')}）—— {reason_str}"
        )

    region_str = "、".join(f"{c} {n} 款" for c, n in country_counter.most_common())
    kw_str = "、".join(f"{k}" for k, _ in kw_counter.most_common(5)) or "无明显关键词热点"

    summary = (
        "【今日 3C 爆品简报（本地汇总版）】\n\n"
        "一、今日爆品 Top5：\n" + "\n".join(top5_lines) + "\n\n"
        f"二、潜力产品：命中“新品/Pro/AI”等关键词的商品值得重点关注，"
        f"本批热点关键词集中在：{kw_str}。\n\n"
        f"三、地区趋势：本次上榜地区分布为 {region_str}。"
        f"主流来源平台为 {platform_counter.most_common(1)[0][0]}。\n\n"
        "四、品类变化：建议持续追踪多地区同时上榜的单品，"
        "这类商品具备较强的全球化爆品潜质。\n\n"
        "（注：未配置 OpenAI Key，本简报由本地规则生成。）"
    )
    return summary


def generate_summary(top_products: List[Dict]) -> str:
    """生成每日 AI 简报；失败时降级为本地模板。"""
    if not OPENAI_API_KEY:
        logger.info("未配置 OPENAI_API_KEY，使用本地模板总结")
        return _local_fallback_summary(top_products)

    try:
        from openai import OpenAI  # 延迟导入，未安装也不影响其他功能

        client_kwargs = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            client_kwargs["base_url"] = OPENAI_BASE_URL
        client = OpenAI(**client_kwargs)

        prompt = _build_prompt(top_products)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你是专业的 3C 跨境电商情报分析师，输出简洁中文。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=800,
        )
        content = resp.choices[0].message.content.strip()
        logger.info("AI 简报生成成功，长度 %d", len(content))
        return content
    except Exception as exc:  # noqa: BLE001 任何 AI 异常都降级
        logger.error("AI 简报生成失败，降级为本地模板: %s", exc)
        return _local_fallback_summary(top_products)
