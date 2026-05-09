# 股票投资辅助工具

个人股票 + 外汇投资辅助 Web 工具：自动扫描行情、给出中文化的多空信号，并提供**虚拟账户**让你在投入真金白银前先验证策略有效性。

> **项目状态：** ✅ 后端 + 虚拟交易 + 前端 + Docker 部署 全部完成；可本机开发或 VPS 上 HTTPS 上线。

---

## 核心特性

### 🔍 智能信号生成
- **短期信号**（日线 + 小时线）：EMA20/50、RSI(14)、MACD、成交量 — 回答「现在进场时机好不好？」
- **长期信号**（日线 + 周线）：EMA50/200 金叉死叉、价格 vs EMA200、长期趋势斜率、周线 RSI — 回答「大方向是涨还是跌？」
- **统一评分**：-4（强烈看跌）到 +4（强烈看涨），中文标签直接告诉你结论
- **缺失数据中性处理**：当某些指标因数据不足无法计算时贡献 0（中性），不再像旧版本一样默认偏空

### 📊 机会发现
- 自动扫描 38 只标普 500 蓝筹股 + 20 个主要外汇对
- 按短期 / 长期信号强度排序
- 美股每个交易日收盘后扫描（21:05 UTC），外汇每 4 小时扫描一次
- 支持手动「立即扫描」按钮，前端轮询完成自动刷新

### 📌 自选监控 + 异常告警
- 自选标的的异常信号（评分跳变、强烈信号、RSI 超买超卖）触发邮件 + Web Push 通知
- 通知历史 30 条；未读角标实时显示

### 💼 虚拟交易（核心新功能）
- $100,000 默认虚拟账户，**支持市价 + 限价单**
- 闭市时段下美股订单会排队，下次开盘自动成交
- 外汇 24h 即时成交，含 0.5 pip 模拟点差
- 每张订单自动记录下单时的信号快照（label + score），便于回看「按信号下单的胜率」
- 持仓总览页：现金 / 市值 / 累计盈亏 / 净值曲线
- 可信架构：`BrokerAdapter` 抽象层让未来接入真实经纪商（Alpaca、IB）零成本切换

### 🤖 深度分析（可选）
- 集成 Anthropic Claude API，按需生成约 200 字中文投资分析
- 不开 key 也不影响其他功能（API 返回 501）

---

## 技术栈

| 层 | 选型 |
|---|---|
| **后端** | Python 3.11 / FastAPI 0.115 / aiosqlite / APScheduler |
| **数据源** | yfinance（免费，约 15 分钟延迟）+ 自带 query2 直连降级 |
| **指标** | pandas-ta-classic |
| **认证** | JWT (HS256, 30 天) + 单密码登录 |
| **前端** | Next.js 16 (App Router) / React 19 / TypeScript / Tailwind v4 / Recharts |
| **数据库** | SQLite |
| **部署** | Docker Compose + nginx + Let's Encrypt 自动续期 |
| **可选 AI** | Anthropic Claude API |

---

## 快速开始

### 路径 A：本机开发（最快）

需要 Python 3.11+ 与 Node.js 20+。

**后端**

```bash
cd stock-tool/backend
python -m venv venv
.\venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# 准备 .env（最少两项）
echo "APP_PASSWORD=你的密码" > .env
# 用 PowerShell 生成 64 字符 SECRET_KEY 加到 .env
# -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | % {[char]$_})

uvicorn main:app --reload --port 8000
```

后端起来后 `http://localhost:8000/health` 应返回 `{"status":"ok"}`，API 文档在 `/docs`。

**前端**（另开一个终端）

```bash
cd stock-tool/frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:3000` → 自动跳到 `/login` → 输入 `APP_PASSWORD` → 进入 dashboard。

### 路径 B：Docker 本机集成测试

需要 Docker Desktop。

```bash
cd stock-tool
cp .env.example .env
# 编辑 .env，至少填写 APP_PASSWORD 和 SECRET_KEY

docker compose up --build -d
```

访问 `http://localhost`（nginx 反代）即可。

### 路径 C：VPS 部署 + HTTPS

参见 [`stock-tool/DEPLOYMENT.md`](stock-tool/DEPLOYMENT.md) — 包含 Ubuntu VPS 安装 Docker、上传项目、Let's Encrypt 证书、HTTPS 切换、维护与故障排查的完整 runbook。

---

## 项目结构

```
stock-tool/
├── backend/                       # FastAPI 后端
│   ├── routers/                  # HTTP 路由
│   │   ├── auth.py              # 单密码登录 + JWT
│   │   ├── watchlist.py         # 自选 CRUD
│   │   ├── scanner.py           # 扫描结果查询 + 触发
│   │   ├── alerts.py            # 价格/信号提醒 CRUD + 历史
│   │   ├── analysis.py          # 单标的指标 + 深度分析
│   │   └── portfolio.py         # 虚拟账户 + 订单 + NAV
│   ├── services/
│   │   ├── data_fetcher.py      # yfinance + query2 双路径
│   │   ├── indicator_engine.py  # EMA/RSI/MACD/成交量
│   │   ├── signal_engine.py     # 评分规则 + 中文模板
│   │   ├── scanner_service.py   # 批量扫描 + matcher 触发
│   │   ├── notifier.py          # SMTP 邮件 + 历史落库
│   │   ├── scheduler.py         # 3 个 cron job
│   │   ├── market_hours.py      # 美股开闭市判定
│   │   ├── order_matcher.py     # 限价/排队订单撮合
│   │   └── nav_service.py       # 每日净值快照
│   ├── brokers/
│   │   ├── base.py              # BrokerAdapter Protocol + 异常类型
│   │   ├── paper.py             # PaperBrokerAdapter（事务化）
│   │   └── registry.py          # paper_adapter 单例
│   ├── data/universe.py         # SP500 + FX 标的池
│   ├── tests/                   # 143 个单元/集成测试
│   ├── main.py / config.py / database.py / models.py
│   └── Dockerfile
│
├── frontend/                     # Next.js 16 前端
│   ├── app/
│   │   ├── login/               # 登录页
│   │   ├── dashboard/           # 仪表盘 + 持仓摘要
│   │   ├── opportunities/       # 机会发现 + 筛选
│   │   ├── symbol/[ticker]/     # 详情页 + 虚拟下单
│   │   ├── alerts/              # 价格/信号/历史 三 tab
│   │   ├── portfolio/           # 持仓总览 + 净值曲线
│   │   └── portfolio/orders/    # 交易历史 + 取消
│   ├── components/              # SignalBadge/Card, NavBar, OrderModal 等 17 个
│   ├── lib/                     # types / api / auth
│   ├── public/sw.js             # Web Push Service Worker
│   ├── middleware.ts            # cookie 路由守卫
│   └── Dockerfile
│
├── nginx/
│   ├── nginx.conf              # HTTP — Let's Encrypt 验证用
│   └── nginx-ssl.conf          # HTTPS — 含 YOUR_DOMAIN 占位
│
├── docker-compose.yml          # 本地基础栈
├── docker-compose.prod.yml     # HTTPS 叠加 + certbot 自动续期
├── .env.example                # 配置模板
└── DEPLOYMENT.md               # 部署 runbook
```

---

## API 端点摘要

所有受保护路由需要 `Authorization: Bearer <jwt>` header。

| 模块 | 端点 |
|---|---|
| **认证** | `POST /auth/login` |
| **自选** | `GET /watchlist`、`POST /watchlist`、`DELETE /watchlist/{ticker}` |
| **扫描** | `GET /scanner/results?market=&signal_type=&sort_by=`、`POST /scanner/trigger`、`GET /scanner/last-scan-time` |
| **分析** | `GET /analysis/{ticker}`、`POST /analysis/{ticker}/deep` |
| **提醒** | `GET\|POST\|DELETE /alerts/price`、`/alerts/signal`、`GET /alerts/history`、`GET /alerts/unread-count`、`POST /alerts/history/{id}/read` |
| **虚拟交易** | `GET /portfolio/accounts`、`GET\|POST /portfolio/accounts/{id}/orders`、`DELETE /portfolio/accounts/{id}/orders/{order_id}`、`GET /portfolio/accounts/{id}/positions`、`GET /portfolio/accounts/{id}/nav-history?days=`、`GET /portfolio/accounts/{id}/performance` |

完整 API 自描述文档：启动后端后访问 `http://localhost:8000/docs`。

---

## 信号系统

### 评分映射

| 分值 | 标签 | 含义 |
|---|---|---|
| +3 ~ +4 | 🟢 强烈看涨 | 多个强势信号一致；短期买点明确 |
| +1 ~ +2 | 🟢 看涨信号 | 偏多，可关注 |
| 0 | 🟡 中性观望 | 信号混杂或数据稀缺；建议观望 |
| -1 ~ -2 | 🔴 看跌信号 | 偏空，谨慎 |
| -3 ~ -4 | 🔴 强烈看跌 | 多个卖出信号一致；短期风险高 |

### 4 + 4 指标体系

**短期（日线）：** EMA20 vs EMA50、RSI(14)、MACD(12,26,9)、当日成交量 vs 20 日均量

**长期（日线 + 周线）：** EMA50 vs EMA200、当前价 vs EMA200、EMA200 斜率（20 日）、周线 RSI

每个指标贡献 +1 / -1 / **0（数据不足时中性）**，4 个指标加总即评分。

### 虚拟交易撮合规则

- **市价单**：开市瞬间按当时价成交；闭市时段美股先排队，下次开盘自动成交（外汇 24h 不排队）
- **限价单**：每轮扫描周期检查（美股 21:05、外汇每 4h），价格穿越限价时按限价成交
- **手续费**：股票零佣金；外汇买卖各 0.5 pip 点差（`PAPER_FX_SPREAD_PIPS` 可配）

---

## 配置 (.env)

| 变量 | 必填 | 说明 |
|---|---|---|
| `APP_PASSWORD` | ✅ | 登录密码 |
| `SECRET_KEY` | ✅ | JWT 签名密钥（建议 64 字符随机串） |
| `DATABASE_URL` | | 默认 `./data.db`（容器中通常 `/data/data.db`） |
| `SMTP_HOST` / `SMTP_PORT` | | 默认 `smtp.gmail.com:587` |
| `SMTP_USER` / `SMTP_PASS` | | Gmail 应用专用密码（开两步验证后生成） |
| `NOTIFY_EMAIL` | | 收件邮箱；不配则邮件功能静默跳过 |
| `CLAUDE_API_KEY` | | 不配则深度分析返回 501，其他功能不受影响 |
| `PAPER_INITIAL_CASH` | | 默认 100000.0 |
| `PAPER_FX_SPREAD_PIPS` | | 默认 0.5；设 0 关闭点差 |

完整模板见 `stock-tool/.env.example`。

---

## 测试

```bash
cd stock-tool/backend
pytest -q -m "not network"          # 143 个非网络测试，约 10 秒
pytest -q -m network                # 4 个真实 yfinance 测试（需联网）
```

测试覆盖：schema 迁移、broker 撮合（市价 / 限价 / 排队 / 拒绝 / 信号快照 / 不变量）、市场时段、NAV 快照、portfolio API、扫描器与 matcher 集成、通知录入。

---

## 文档

- [`docs/superpowers/specs/2026-04-27-stock-investment-tool-design.md`](docs/superpowers/specs/2026-04-27-stock-investment-tool-design.md) — 设计文档（含虚拟交易模块）
- [`docs/superpowers/plans/2026-04-27-stock-tool-backend.md`](docs/superpowers/plans/2026-04-27-stock-tool-backend.md) — 后端实施计划
- [`docs/superpowers/plans/2026-05-06-stock-tool-paper-trading-backend.md`](docs/superpowers/plans/2026-05-06-stock-tool-paper-trading-backend.md) — 虚拟交易后端
- [`docs/superpowers/plans/2026-04-27-stock-tool-frontend.md`](docs/superpowers/plans/2026-04-27-stock-tool-frontend.md) — 前端实施计划
- [`docs/superpowers/plans/2026-04-27-stock-tool-deployment.md`](docs/superpowers/plans/2026-04-27-stock-tool-deployment.md) — 部署实施计划
- [`stock-tool/DEPLOYMENT.md`](stock-tool/DEPLOYMENT.md) — **部署 runbook**（本机 Docker 验证 + VPS HTTPS）

---

## 风险提示

⚠️ **本工具仅供个人参考，不构成投资建议。**

- 行情数据来自 yfinance，约 **15 分钟延迟**
- 信号引擎是规则化的技术指标组合，**不是预测模型**
- 虚拟交易撮合按延迟价格成交，**与真实交易存在滑点差异**
- 强烈建议：**先在虚拟账户跑足够长时间**（至少几周），观察策略真实胜率，再考虑接入真实经纪商
- 妥善保管 `.env`（含密码 / API key）；不要 commit 到 git

---

## 后续规划（已预留接口，未实装）

- **真实经纪商接入**：`BrokerAdapter` 接口已可用；接 Alpaca/IB 仅需新建 `brokers/alpaca.py` 实装协议方法
- **MCP server**：架构预留为 stdio 内部工具调用；可让 Claude Desktop 直接读取信号、下单
- **止损订单类型**
- **更多技术指标**：布林带、ADX、OBV
- **策略回测**：基于已存的信号快照 + 订单历史

---

## License

MIT
