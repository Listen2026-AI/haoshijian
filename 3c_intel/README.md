# 3C 爆品情报自动收集系统

每天自动收集 **中国 / 日本 / 欧洲** 的 3C 产品爆品信息，进行评分排序与 AI 分析，
并在每天早上 8 点生成日报推送到 **企业微信**。

---

## 一、项目结构

```
3c_intel/
├── main.py               # 主流程入口：采集→去重→评分→AI总结→推送→存档
├── scheduler.py          # 定时调度器（Python schedule 方式，每天 08:00）
├── config.py             # 全局配置（数据源、评分权重、密钥从环境变量读取）
├── requirements.txt      # 依赖列表
├── .env.example          # 环境变量模板（复制为 .env 填入密钥）
├── .gitignore
├── README.md
│
├── crawler/              # 数据采集模块
│   ├── __init__.py       #   collect_all()：聚合所有数据源
│   ├── base.py           #   HTTP 请求封装（重试/超时/限速）+ 商品结构
│   ├── amazon_jp.py      #   Amazon 日本 Best Sellers
│   ├── amazon_eu.py      #   Amazon 德国 / 英国 Best Sellers
│   └── jd.py             #   京东热卖（按销量排序的搜索结果作替代榜单）
│
├── analyzer/             # 数据处理与分析模块
│   ├── __init__.py
│   ├── scorer.py         #   爆品评分算法（排名+多平台+关键词）
│   └── ai_summary.py     #   OpenAI 简报生成（无 key 时本地模板降级）
│
├── notifier/             # 推送模块
│   ├── __init__.py
│   └── wechat.py         #   企业微信群机器人推送（自动分段）
│
├── utils/                # 通用工具
│   ├── __init__.py
│   ├── logger.py         #   统一日志（控制台 + 按天滚动文件）
│   ├── cache.py          #   文件缓存（默认 6 小时，避免重复抓取）
│   └── dedup.py          #   商品去重 + 多来源统计
│
├── data/                 # 缓存与每日报告存档（自动生成）
└── logs/                 # 运行日志（自动生成）
```

---

## 二、安装步骤

```bash
# 1. 进入项目目录
cd 3c_intel

# 2. （推荐）创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量：复制模板并填入真实值
cp .env.example .env
# 然后编辑 .env，至少填入 WECHAT_WEBHOOK_KEY
```

---

## 三、配置说明

所有密钥通过环境变量读取（写在 `.env` 中），不硬编码到源码。

| 变量 | 必填 | 说明 |
|------|------|------|
| `WECHAT_WEBHOOK_KEY` | ✅ | 企业微信群机器人 webhook 的 key（见下文第六节） |
| `OPENAI_API_KEY` | ❌ | OpenAI key；不填则自动使用**本地模板**生成简报 |
| `OPENAI_BASE_URL` | ❌ | 自定义 API 网关/代理地址（可选） |
| `OPENAI_MODEL` | ❌ | 模型名，默认 `gpt-4o-mini` |
| `SCHEDULE_TIME` | ❌ | 定时执行时间 `HH:MM`，默认 `08:00` |

数据源类目、评分权重、抓取数量等均可在 `config.py` 中调整。

---

## 四、如何运行

**立即执行一次完整流程**（采集 → 评分 → AI 总结 → 推送 → 存档）：

```bash
python main.py
```

**调试用开关**（本地验证很方便）：

```bash
# 只测采集：抓取并打印每条结果，不评分/不总结/不推送
python main.py --collect-only

# 跑完整流程并存档，但跳过企业微信推送（本地没配 webhook 时用这个看产出）
python main.py --no-push
```

执行后：
- 日报会推送到企业微信群；
- 结果同时存档到 `data/report_YYYYMMDD.json`；
- 运行日志写入 `logs/app.log`。

---

## 五、如何部署定时任务

### 方式 A：Python schedule（开发 / 简单场景，需进程常驻）

```bash
python scheduler.py
```

进程会常驻，每天 `SCHEDULE_TIME`（默认 08:00）自动执行。
可配合 `nohup` / `screen` / `tmux` 后台运行：

```bash
nohup python scheduler.py > logs/scheduler.out 2>&1 &
```

### 方式 B：系统 cron（推荐，服务器生产环境，无需常驻）

```bash
crontab -e
```

添加一行（注意把路径换成你的实际路径，并指定虚拟环境的 python）：

```cron
# 每天早上 8:00 执行
0 8 * * * cd /path/to/3c_intel && /path/to/3c_intel/.venv/bin/python main.py >> logs/cron.log 2>&1
```

> cron 不会加载交互式 shell 的环境变量，因此密钥务必写在项目的 `.env` 文件里
> （程序通过 python-dotenv 自动加载），而不是依赖 shell export。

---

## 六、企业微信配置方法（创建 Bot）

1. 打开**企业微信**，进入任意内部群聊（或新建一个群）。
2. 点击群右上角 `...` → 「群机器人」→「添加机器人」→「新建一个机器人」。
3. 命名（如「3C爆品情报」），创建后得到 Webhook 地址：
   ```
   https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXXXXXXX-XXXX-XXXX
   ```
4. 复制 `key=` 后面的字符串，填入 `.env`：
   ```
   WECHAT_WEBHOOK_KEY=XXXXXXXX-XXXX-XXXX
   ```
5. 运行 `python main.py` 测试，群里应收到日报卡片。

---

## 七、评分算法说明

```
score = 排名权重 + 多平台出现加分 + 关键词命中加分
```

- **排名权重**：第 1 名满分（默认 100），按排名线性递减。
- **多平台加分**：同一商品在多个平台/地区榜单出现，每多一个来源 +30（去重时统计）。
- **关键词加分**：命中 `新品 / 新款 / Pro / Max / Ultra / AI / 智能 / 旗舰 / New / 2026` 等热点词加分。

权重均可在 `config.py` 的 `RANK_BASE_SCORE` / `MULTI_SOURCE_BONUS` / `KEYWORD_SCORES` 调整。

---

## 八、额外特性

- **自动去重**：`utils/dedup.py` 按商品名归一化指纹合并重复项，并统计多来源出现次数（用于加分）。
- **本地缓存**：`utils/cache.py` 默认缓存 6 小时，避免短时间重复抓取同一榜单。
- **日志记录**：`utils/logger.py` 同时输出控制台与按天滚动文件（保留 14 天）。
- **优雅降级**：任一数据源失败不影响其他源；无 OpenAI key 时自动用本地模板生成简报；推送失败有日志告警。

---

## 九、关于反爬的重要说明（务必阅读）

Amazon Best Sellers 与京东榜单/搜索页都有**较强的反爬机制**，对来自
**云服务器 / 数据中心 IP** 的请求经常直接返回 `403` 或空页面。本项目已做：

- 真实浏览器请求头、限速、指数退避重试；
- 多套 HTML 选择器兜底；
- 单源失败隔离，不影响整体流程。

但要在生产环境**稳定拿到数据**，通常还需要以下之一（按需选用）：

1. **住宅代理 / 海外代理 IP**（最有效，把请求出口换成真实用户网络）。
2. **Playwright 渲染**：当页面内容必须由 JS 渲染才能获取时启用。
   - 已在 `requirements.txt` 注释中预留，启用步骤：
     ```bash
     pip install playwright
     playwright install chromium
     ```
   - 之所以默认用 `requests + BeautifulSoup`：更轻量、更快、资源占用低；
     Playwright 仅在“静态请求拿不到内容”时作为升级方案。
3. 官方/半官方数据接口或第三方榜单 API。

> 在本地真实网络环境下运行成功率明显更高。代码逻辑本身是完整可运行的，
> 数据为空时通常是被目标站点反爬拦截，而非代码错误（查看 `logs/app.log` 可确认状态码）。
