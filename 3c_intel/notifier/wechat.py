"""
企业微信群机器人推送
====================

【如何创建企业微信群机器人 Bot】
1. 打开企业微信，进入任意一个内部群聊（或新建一个群）。
2. 点击群右上角「...」-> 「群机器人」-> 「添加机器人」-> 「新建一个机器人」。
3. 设置机器人名称（如「3C爆品情报」），创建完成后会得到一个 Webhook 地址：
   https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXXXXXXX-XXXX-XXXX
4. 复制其中 key= 后面的字符串，配置到环境变量 WECHAT_WEBHOOK_KEY。
   （建议写入项目根目录 .env 文件：WECHAT_WEBHOOK_KEY=你的key）

代码通过环境变量读取 key，不在源码中硬编码，安全可控。

接口说明：群机器人 markdown 消息单条最长约 4096 字节，超长会自动分段发送。
"""

from typing import Dict, List

from config import TOP_N_REPORT, WECHAT_WEBHOOK_URL
from utils.logger import get_logger

from crawler.base import http_post

logger = get_logger("notifier.wechat")

MAX_MARKDOWN_BYTES = 4000  # 留出余量，低于企业微信 4096 上限


def _build_markdown(top_products: List[Dict], ai_summary: str) -> str:
    """构造企业微信 markdown 消息内容。"""
    from datetime import datetime

    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 📱 3C 爆品情报日报（{date_str}）", ""]

    # 1) 爆品榜 Top N
    lines.append(f"## 🔥 今日爆品榜 Top {TOP_N_REPORT}")
    for i, p in enumerate(top_products[:TOP_N_REPORT], start=1):
        name = p.get("name", "")[:36]
        price = p.get("price") or "—"
        tag = f"`{p.get('country')}/{p.get('platform')}`"
        score = p.get("score")
        link = p.get("link", "")
        title = f"[{name}]({link})" if link else name
        lines.append(
            f"**{i}.** {title}\n"
            f"> {tag} 价格:{price} 评分:**{score}**"
        )

    # 2) AI 简报
    lines.append("")
    lines.append("## 🤖 AI 情报简报")
    lines.append(ai_summary)

    return "\n".join(lines)


def _split_text(text: str, max_bytes: int = MAX_MARKDOWN_BYTES) -> List[str]:
    """按字节长度将长文本分段，避免超过企业微信单条上限。"""
    chunks: List[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = current + line + "\n"
        if len(candidate.encode("utf-8")) > max_bytes and current:
            chunks.append(current)
            current = line + "\n"
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _send_markdown(content: str) -> bool:
    """发送单条 markdown 消息。"""
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    resp = http_post(WECHAT_WEBHOOK_URL, json_body=payload)
    if resp is None:
        return False
    try:
        data = resp.json()
        if data.get("errcode") == 0:
            return True
        logger.error("企业微信返回错误: %s", data)
        return False
    except ValueError:
        logger.error("企业微信返回非 JSON: %s", resp.text[:200])
        return False


def send_report(top_products: List[Dict], ai_summary: str) -> bool:
    """
    推送完整日报（爆品榜 + AI 总结）到企业微信。
    返回是否全部发送成功。
    """
    if not WECHAT_WEBHOOK_URL:
        logger.error("未配置 WECHAT_WEBHOOK_KEY，无法推送。请设置环境变量后重试。")
        return False

    content = _build_markdown(top_products, ai_summary)
    chunks = _split_text(content)

    all_ok = True
    for idx, chunk in enumerate(chunks, start=1):
        ok = _send_markdown(chunk)
        if ok:
            logger.info("企业微信推送成功（第 %d/%d 段）", idx, len(chunks))
        else:
            logger.error("企业微信推送失败（第 %d/%d 段）", idx, len(chunks))
            all_ok = False
    return all_ok
