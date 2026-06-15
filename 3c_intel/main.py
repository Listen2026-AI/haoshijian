"""
主流程入口
==========
串联：采集 -> 去重 -> 评分 -> AI 总结 -> 企业微信推送 -> 落盘存档。

直接运行执行一次完整流程：
    python main.py
"""

import json
from datetime import datetime

from config import DATA_DIR, TOP_N_REPORT
from crawler import collect_all
from analyzer import generate_summary, score_products, top_n
from notifier import send_report
from utils.dedup import dedup_products
from utils.logger import get_logger

logger = get_logger("main")


def _archive(scored, ai_summary):
    """将当日结果落盘存档，便于回溯与后续分析。"""
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = DATA_DIR / f"report_{date_str}.json"
    payload = {
        "date": date_str,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_products": scored[:TOP_N_REPORT],
        "ai_summary": ai_summary,
    }
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info("已存档: %s", out_path)
    except OSError as exc:
        logger.error("存档失败: %s", exc)


def run_once(collect_only: bool = False, no_push: bool = False) -> bool:
    """
    执行一次完整情报收集与推送流程。

    参数：
      collect_only：只采集并打印结果，不评分/不总结/不推送（用于调试数据源）。
      no_push：跑完整流程但跳过企业微信推送（用于本地无 webhook 时验证产出）。
    返回是否成功（推送成功，或在 no_push/collect_only 模式下表示流程正常）。
    """
    logger.info("=" * 50)
    logger.info("3C 爆品情报流程开始（collect_only=%s, no_push=%s）", collect_only, no_push)

    # 1. 采集
    products = collect_all()

    # 仅采集模式：直接打印每个商品，便于调试数据源是否正常
    if collect_only:
        logger.info("仅采集模式，共 %d 条：", len(products))
        for p in products:
            logger.info(
                "  [%s/%s] #%s %s | %s",
                p.get("country"), p.get("platform"), p.get("rank"),
                (p.get("name") or "")[:40], p.get("price") or "—",
            )
        return bool(products)

    if not products:
        logger.warning("未采集到任何商品，流程结束（可能全部数据源被反爬或网络异常）。")
        if no_push:
            return False
        # 仍尝试推送一条提醒
        return send_report([], "今日未采集到有效数据，请检查数据源 / 网络 / 反爬策略。")

    # 2. 去重（同时统计多来源出现次数）
    deduped = dedup_products(products)

    # 3. 评分排序
    scored = score_products(deduped)
    report_top = top_n(scored, TOP_N_REPORT)

    # 4. AI 总结
    ai_summary = generate_summary(report_top)

    # 5. 推送（no_push 模式跳过）
    if no_push:
        logger.info("no_push 模式：跳过企业微信推送。Top%d 预览：", TOP_N_REPORT)
        for i, p in enumerate(report_top, start=1):
            logger.info("  %d. score=%s | %s", i, p.get("score"), (p.get("name") or "")[:40])
        ok = True
    else:
        ok = send_report(report_top, ai_summary)

    # 6. 存档
    _archive(scored, ai_summary)

    logger.info("3C 爆品情报流程结束，结果: %s", "成功" if ok else "失败")
    logger.info("=" * 50)
    return ok


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="3C 爆品情报自动收集系统")
    parser.add_argument(
        "--collect-only", action="store_true",
        help="只测采集并打印结果，不评分/不总结/不推送",
    )
    parser.add_argument(
        "--no-push", action="store_true",
        help="跑完整流程并存档，但跳过企业微信推送",
    )
    args = parser.parse_args()
    run_once(collect_only=args.collect_only, no_push=args.no_push)
