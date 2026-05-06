# 股票投资辅助工具 — 设计文档

**日期：** 2026-04-27（初版）/ 2026-05-06（追加虚拟交易模块）
**状态：** 已批准

---

## 1. 项目背景与目标

开发一个 Web 端个人股票/外汇投资辅助工具，帮助没有技术分析经验的用户发现潜在投资机会、监控自选标的异常信号，并通过通知系统及时提醒。

**核心设计原则：** 用户只看中文结论，不需要理解技术指标的原始数字。

**投资风格：** 技术面为主（短线），基本面作参考。  
**目标市场：** 美股（标普500成分股）+ 主要外汇对（EUR/USD、GBP/USD、USD/JPY、USD/CHF、AUD/USD、USD/CAD、NZD/USD 等约20对，含主要对和交叉盘）。  
**风险偏好：** 小额可接受损失资产，适合中高风险操作。

---

## 2. 技术栈

| 层次 | 技术选型 |
|---|---|
| 前端 | Next.js + Tailwind CSS（响应式，支持手机浏览器） |
| 后端 | Python + FastAPI |
| 数据库 | SQLite（单用户，无需额外配置） |
| 技术指标计算 | pandas-ta |
| 数据源 | yfinance（美股 + 外汇，免费，约15分钟延迟） |
| 定时任务 | APScheduler |
| 通知 | Web Push + SMTP 邮件 |
| 可选 AI 分析 | Claude API（按需调用，非必要路径） |
| 部署 | Docker Compose + nginx（VPS 远程部署） |

---

## 3. 核心页面

### 3.1 仪表盘（首页）
- 自选列表：已关注品种的当前价格、涨跌幅、短期/长期信号标签
- 异常信号高亮：触发异常的自选品种卡片边框变色（红/橙），顶部显示警告横幅
- 页面标题栏角标显示未处理的异常数量
- 今日扫描摘要：发现 N 个看涨信号、M 个看跌信号
- 快速入口：跳转到机会发现页

### 3.2 机会发现
- 系统自动扫描标普500成分股 + 20个主要外汇对
- 卡片列表布局，每张卡片显示：
  - 品种代码、中文全称
  - 行业板块标注（如：信息技术 · 半导体）
  - 短期信号标签 + 长期信号标签
  - 一句话结论描述
  - 当前价格与涨跌幅
- 默认按**短期信号强度**排序，可切换为长期
- 顶部筛选栏：全部 / 美股 / 外汇，信号类型（看涨 / 看跌）
- 上次扫描时间 + 手动触发「立即扫描」按钮

### 3.3 品种详情页
- 价格走势图（近30天，折线）
- 信号摘要分为两个独立区块：
  - **短期信号**（EMA 20/50、RSI 日线、MACD 日线/小时线、成交量变化）
  - **长期信号**（EMA 50/200、RSI 周线、长期趋势方向）
- 每个指标显示原始数值 + 中文说明
- 综合评分：短期 X/4 分，长期 X/4 分
- 「加入自选」按钮
- 「🤖 深度分析」按钮（调用 Claude API，生成约200字中文分析，按需使用）

### 3.4 持仓与交易（虚拟交易）

**入口：** 顶部导航 + 品种详情页「虚拟下单」按钮（仅此入口；机会发现卡片不放下单按钮）

**3.4.1 持仓总览页**
- 顶部摘要卡：现金余额、持仓市值、账户净值、累计盈亏（金额 + 百分比）、今日盈亏
- 净值曲线：自账户创建以来每日收盘净值折线图
- 持仓列表（卡片）：品种、当前价、持仓数量、平均成本、浮动盈亏、当前信号标签
- 每张持仓卡片可一键跳转到品种详情页

**3.4.2 下单弹窗（从详情页触发）**
- 显示：标的、当前价、可用现金、最大可买数量
- 表单：方向（买/卖）、订单类型（市价/限价）、数量、限价（仅限价单）
- **自动预填**当前信号标签和评分（不可编辑，仅作为快照存档）
- 美股闭市时段下单：提示「将在下次开盘后排队成交」
- 提交前二次确认弹窗

**3.4.3 交易历史页**
- 时间线列表：每条订单显示时间、品种、方向、数量、成交价、订单状态、下单时信号标签
- 筛选：账户、订单状态（已成交/已取消/待成交）、信号类型（短期/长期）、方向
- 限价单可取消（按钮）

### 3.5 提醒管理
两个标签页：

**价格提醒：** 设置当某品种价格突破指定阈值时触发通知

**信号提醒：** 监控自选股信号跳变，触发条件包括：
- 信号等级跳变（如 🟡 → 🔴，或 🟡 → 🟢）
- 出现「强烈看涨」或「强烈看跌」信号
- RSI 进入超买（>70）或超卖（<30）区间

历史提醒记录（最近30条）

---

## 4. 信号引擎

### 4.1 指标体系

| 信号类型 | 数据周期 | 使用指标 | 核心问题 |
|---|---|---|---|
| 短期信号 | 日线 + 小时线 | EMA 20/50、RSI (14)、MACD、成交量变化 | 现在进场时机好不好？ |
| 长期信号 | 日线 + 周线 | EMA 50/200（金叉/死叉）、RSI（周线）、趋势方向 | 大方向是涨还是跌？ |

### 4.2 评分规则

每个指标贡献 +1（看涨）或 -1（看跌），汇总得出综合分（-4 到 +4）：

| 分值 | 信号标签 |
|---|---|
| +3 ~ +4 | 🟢 强烈看涨 |
| +1 ~ +2 | 🟢 看涨信号 |
| 0 | 🟡 中性观望 |
| -1 ~ -2 | 🔴 看跌信号 |
| -3 ~ -4 | 🔴 强烈看跌 |

短期与长期各自独立评分，互不影响。

### 4.3 中文模板输出

信号结论通过预设中文模板生成，不依赖 AI，示例：
- EMA 金叉 → "短期均线向上突破长期均线"
- RSI < 30 → "当前处于超卖区，可能出现反弹"
- MACD 金叉 → "动能由跌转涨（金叉形成）"
- 成交量 +30% → "成交量同步放大，信号更可信"

### 4.4 扫描频率

| 市场 | 扫描时机 |
|---|---|
| 美股 | 每个交易日收盘后（美东时间 16:05） |
| 外汇 | 每4小时一次（24小时市场） |

---

## 5. 虚拟交易引擎

### 5.1 核心目的

让用户在投入真金白银之前，用工具给出的信号在虚拟账户上进行模拟买卖，验证系统建议的有效性。同时为未来对接真实经纪商账户预留架构插槽。

### 5.2 经纪商抽象层

引入 `BrokerAdapter` 抽象接口，所有下单逻辑只依赖该接口：

```python
class BrokerAdapter(Protocol):
    def get_account(self, account_id: str) -> AccountInfo
    def get_positions(self, account_id: str) -> list[Position]
    def get_orders(self, account_id: str, status: str | None) -> list[Order]
    def place_order(self, account_id: str, request: OrderRequest) -> Order
    def cancel_order(self, account_id: str, order_id: str) -> Order
```

**MVP 实装：** `PaperBrokerAdapter`（纯 SQLite 实装）
**预留：** `AlpacaBrokerAdapter`、`IBBrokerAdapter`（未在本轮实装；目标券商**暂不锁定**）

切换到真实账户 = 替换 adapter，业务层零改动。

### 5.3 账户模型

- **MVP 暴露单一虚拟账户**给 UI（账户名 `default`、初始资金 **$100,000 USD**）
- DB schema 支持多账户，便于后期扩展「策略 A 账户 vs 策略 B 账户」对比
- 真实账户在未来作为 `type=real` 接入，UI 添加账户切换器

### 5.4 订单类型与撮合规则

| 类型 | MVP | 撮合时机 | 成交价 |
|---|---|---|---|
| 市价单 | ✅ | 提交瞬间 | 最新 yfinance 价格（15 分钟延迟） |
| 限价单 | ✅ | 每轮扫描周期检查 | 触发时按限价 |
| 止损单 | ❌ 后期 | — | — |

**美股闭市时段提交：** 订单状态 `queued`，挂入待办；下一次美股扫描周期（21:05）开市后转为 `pending` 并按当时价格成交。
**外汇：** 24 小时市场，立即按市价成交；限价单沿用 4 小时扫描周期检查。

**手续费模型：**
- 美股：零佣金
- 外汇：双边各 0.5 pip 点差（买价上浮、卖价下浮，可在 `.env` 关闭）

### 5.5 信号快照（强制）

每次下单**强制**记录下单瞬间的：
- `signal_label_short`（如「🟢 看涨信号」）
- `signal_score_short`（-4 ~ +4）
- `signal_label_long`、`signal_score_long`
- `triggered_by`：`manual`（用户手动）/ `recommendation`（来自机会发现）

未来可基于这份快照计算「按短期看涨信号下单的胜率」「按强烈看涨信号下单的累计回报」等回测式指标。

### 5.6 数据表新增

```sql
CREATE TABLE accounts (
  id TEXT PRIMARY KEY,           -- e.g. 'default'
  type TEXT NOT NULL,            -- 'paper' | 'real'
  broker_adapter TEXT NOT NULL,  -- 'paper' | 'alpaca' | 'ib'
  display_name TEXT NOT NULL,
  initial_cash REAL NOT NULL,
  cash_balance REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE orders (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,                -- 'buy' | 'sell'
  order_type TEXT NOT NULL,          -- 'market' | 'limit'
  qty REAL NOT NULL,
  limit_price REAL,                  -- NULL for market
  status TEXT NOT NULL,              -- 'queued'|'pending'|'filled'|'cancelled'|'rejected'
  fill_price REAL,
  fill_qty REAL,
  fee REAL NOT NULL DEFAULT 0,
  signal_label_short TEXT,
  signal_score_short INTEGER,
  signal_label_long TEXT,
  signal_score_long INTEGER,
  triggered_by TEXT NOT NULL,        -- 'manual' | 'recommendation'
  created_at TEXT NOT NULL,
  filled_at TEXT,
  cancelled_at TEXT,
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE positions (
  account_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  qty REAL NOT NULL,
  avg_cost REAL NOT NULL,
  opened_at TEXT NOT NULL,
  PRIMARY KEY (account_id, ticker)
);

CREATE TABLE nav_history (
  account_id TEXT NOT NULL,
  date TEXT NOT NULL,                -- YYYY-MM-DD
  cash REAL NOT NULL,
  market_value REAL NOT NULL,
  total_value REAL NOT NULL,
  PRIMARY KEY (account_id, date)
);
```

### 5.7 定时任务

- **限价单撮合检查：** 复用现有扫描周期（美股 21:05、外汇每 4 小时），扫描完信号后追加一步「检查限价单触发」
- **闭市队列释放：** 美股扫描开始时，将 `queued` 订单转 `pending` 并按当时价成交
- **每日 NAV 快照：** 每个交易日收盘后（21:30 UTC，比扫描略晚）写入 `nav_history`

### 5.8 MCP 服务（架构预留，本轮不实装）

未来追加独立子包 `stock-tool-mcp/`，作为 **仅供内部工具调用** 的 MCP server：
- 复用同一套 `BrokerAdapter` 接口（不重写业务逻辑）
- 暴露工具：`get_positions`、`place_order`、`get_signals`、`get_watchlist`
- 认证：本地仅由用户的 Claude Code / Claude Desktop 通过 stdio 启动；不暴露 HTTP

本轮 spec 中保留接口约定，避免未来返工；本轮**不在 Plan 1.5 实装范围内**。

---

## 6. 通知系统

**基础层：** 浏览器 Web Push 通知（浏览器在后台时可接收）  
**主力层：** SMTP 邮件通知（无需 App，手机邮件客户端接收）  
**后期可选扩展：** 阿里云短信服务（触发率 100%，约 ¥0.045/条）

通知触发：价格提醒 + 信号异常（跳变或极端值）+ **虚拟订单成交/取消（限价单触发时）**

---

## 7. 部署方案

### 本地开发
```bash
# 前端
npm run dev          # Next.js，端口 3000

# 后端
uvicorn main:app --reload   # FastAPI，端口 8000
```

### 远程部署（VPS）
```yaml
# docker-compose.yml
services:
  frontend:   # Next.js，端口 3000
  backend:    # FastAPI，端口 8000
  nginx:      # 反向代理，对外暴露 443/HTTPS
```

**环境变量（.env）：**
- `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS`
- `CLAUDE_API_KEY`（可选）
- `SECRET_KEY`（会话加密）
- `APP_PASSWORD`（登录密码）
- `PAPER_INITIAL_CASH`（默认 100000）
- `PAPER_FX_SPREAD_PIPS`（默认 0.5；设为 0 关闭点差）

**安全：** 单用户密码登录（密码通过 `.env` 中的 `APP_PASSWORD` 配置，无注册系统），HTTPS 由 nginx + Let's Encrypt 自动证书。

---

## 8. MVP 范围（不在初版内）

以下功能明确不在 MVP 内，待后期迭代：
- 策略回测（与虚拟交易历史结合的统计分析）
- 多用户系统
- 阿里云短信通知
- Telegram Bot 通知
- 集成**真实**资金账户的 broker adapter（Alpaca、IB 等）— 接口已预留
- MCP server 实装（接口已预留）
- AI 生成的投资建议作为默认路径（目前仅按需触发）
- 更多技术指标（如布林带、ADX、OBV 等）
- 止损订单类型

---

## 9. 设计决策记录

| 决策 | 原因 |
|---|---|
| SQLite 而非 PostgreSQL | 个人工具，单用户，零配置 |
| yfinance 免费数据 | 控制成本，延迟15分钟对个人投资者影响可接受 |
| 规则引擎而非纯 AI | 日常零 AI 成本，响应快，逻辑透明 |
| Claude API 按需调用 | 仅在用户主动点击「深度分析」时触发，控制费用 |
| Docker Compose 部署 | 一键部署，环境一致，便于迁移 VPS |
| 虚拟交易先行 | 在投入真金白银前，让用户用同一套信号系统验证有效性 |
| BrokerAdapter 抽象层 | 切换真实账户/MCP server 时业务层零改动；目标券商可后期再选 |
| 强制信号快照 | 每张订单存档当时信号；后期可基于此做按信号类型的胜率回测 |
| 限价单复用扫描周期 | 不引入额外定时任务；订单触发延迟可接受（已与价格延迟 15 分钟一致） |
| 闭市排队成交 | 用户可在任意时段下单，UI 提示「将在下次开盘后排队成交」；避免引入复杂的 GTC/IOC 选项 |
| 单虚拟账户 UI / 多账户 schema | MVP 简单；多策略对比留作未来一行配置即开 |
| MCP 仅内部使用 | stdio 启动、无网络暴露；认证简化为本地信任 |
