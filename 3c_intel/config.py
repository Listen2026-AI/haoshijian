"""
全局配置模块
================
所有可调参数集中在此处管理。
敏感信息（API Key、Webhook 等）一律通过环境变量读取，不写死在代码里。

环境变量可写在项目根目录的 .env 文件中（参考 .env.example），
程序启动时会通过 python-dotenv 自动加载。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 自动加载项目根目录下的 .env 文件
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ----------------------------------------------------------------------
# 路径配置
# ----------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"          # 缓存 / 历史数据
LOG_DIR = BASE_DIR / "logs"           # 日志目录
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------
# 抓取配置
# ----------------------------------------------------------------------
TOP_N_PER_SOURCE = 20        # 每个数据源抓取前 N 个商品
TOP_N_REPORT = 10            # 报告中展示的爆品数量

REQUEST_TIMEOUT = 20         # 单次请求超时（秒）
REQUEST_RETRY = 3            # 请求失败重试次数
REQUEST_DELAY = 2.0          # 每次请求之间的间隔（秒），降低被封风险

# 通用请求头，模拟真实浏览器，降低被反爬概率
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7",
    "Connection": "keep-alive",
}

# 各数据源的榜单 URL 配置（可自由增删类目）
# category：类目名；url：榜单地址；platform/country：用于打标
AMAZON_JP_SOURCES = [
    {
        "category": "电子产品(家电・カメラ・AV)",
        "url": "https://www.amazon.co.jp/gp/bestsellers/electronics/",
        "platform": "Amazon",
        "country": "日本",
    },
]

AMAZON_EU_SOURCES = [
    {
        "category": "Electronics (DE)",
        "url": "https://www.amazon.de/gp/bestsellers/electronics/",
        "platform": "Amazon",
        "country": "德国",
    },
    {
        "category": "Electronics (UK)",
        "url": "https://www.amazon.co.uk/gp/bestsellers/electronics/",
        "platform": "Amazon",
        "country": "英国",
    },
]

# 京东榜单：京东对榜单页强反爬，这里使用其公开的“京东手机热卖榜”等
# 若 HTML 榜单抓取失败，会自动回退到京东 PC 端搜索热卖结果作为替代榜单
JD_SOURCES = [
    {
        "category": "手机数码热卖榜",
        # 京东榜单频道（rank）页面
        "url": "https://api.m.jd.com/api",  # 占位，实际抓取逻辑见 crawler/jd.py
        "search_keyword": "3C数码",
        "platform": "京东",
        "country": "中国",
    },
]

# ----------------------------------------------------------------------
# 评分算法配置
# ----------------------------------------------------------------------
# 排名权重：排名越靠前分数越高（满分 RANK_BASE_SCORE）
RANK_BASE_SCORE = 100
# 多平台/多地区出现，每多出现一次的加分
MULTI_SOURCE_BONUS = 30
# 关键词命中加分配置（关键词 -> 加分）
KEYWORD_SCORES = {
    "新品": 15, "新款": 12, "新一代": 12,
    "pro": 10, "max": 8, "ultra": 10,
    "ai": 18, "智能": 10,
    "旗舰": 12, "限量": 10,
    "new": 12, "2025": 8, "2026": 10,
}

# ----------------------------------------------------------------------
# OpenAI / AI 总结配置
# ----------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # 可选：自定义网关/代理地址
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ----------------------------------------------------------------------
# 企业微信推送配置
# ----------------------------------------------------------------------
# 企业微信群机器人 Webhook Key（在群里添加机器人后获得）
# 完整 webhook：https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx
WECHAT_WEBHOOK_KEY = os.getenv("WECHAT_WEBHOOK_KEY", "")
WECHAT_WEBHOOK_URL = (
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
    + WECHAT_WEBHOOK_KEY
    if WECHAT_WEBHOOK_KEY
    else ""
)

# ----------------------------------------------------------------------
# 定时任务配置
# ----------------------------------------------------------------------
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "08:00")  # 每天运行时间 HH:MM
