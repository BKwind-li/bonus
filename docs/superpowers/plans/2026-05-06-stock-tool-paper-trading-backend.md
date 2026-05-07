# 股票工具 — 虚拟交易后端实施计划（Plan 1.5）

**日期：** 2026-05-06
**前置依赖：** Plan 1（后端基础）已完成于 SHA `6c1e8c8`
**目标：** 在现有后端基础上，叠加虚拟交易（paper trading）能力，并通过 BrokerAdapter 抽象层为未来真实经纪商接入与 MCP server 预留架构槽位。

---

## 范围

本计划只覆盖**虚拟交易后端**。不含：
- 前端 UI（在 Plan 2 追加任务）
- MCP server 实装（架构预留，后期单独迭代）
- 真实经纪商 adapter（接口定义留位，不实装）
- 部署变更（Plan 3）

---

## 文件结构

```
stock-tool/backend/
├── brokers/                       # 新增子包
│   ├── __init__.py
│   ├── base.py                    # BrokerAdapter Protocol + 数据类
│   └── paper.py                   # PaperBrokerAdapter 实装
├── services/
│   ├── market_hours.py            # 新增：美股开闭市判定
│   ├── order_matcher.py           # 新增：限价单/排队订单撮合
│   ├── nav_service.py             # 新增：NAV 快照计算与写入
│   └── scheduler.py               # 修改：扫描后追加撮合 + 每日 NAV 任务
├── routers/
│   └── portfolio.py               # 新增：/portfolio/* 路由
├── database.py                    # 修改：init_db 追加 4 张新表 + 默认账户种子
├── models.py                      # 修改：追加 Order、Position、Account、NavPoint Pydantic 模型
├── config.py                      # 修改：追加 paper_initial_cash、paper_fx_spread_pips
└── tests/
    ├── test_brokers_paper.py
    ├── test_market_hours.py
    ├── test_order_matcher.py
    ├── test_nav_service.py
    └── test_routers_portfolio.py
```

---

## Task 1: 数据模型与 schema 迁移

**目标：** 引入 4 张新表，main.py 启动时自动建表并写入默认 paper 账户。

**修改文件：** `database.py`、`models.py`

### 1.1 database.py — 在 init_db 的 SQL script 中追加

```sql
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  broker_adapter TEXT NOT NULL,
  display_name TEXT NOT NULL,
  initial_cash REAL NOT NULL,
  cash_balance REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  order_type TEXT NOT NULL,
  qty REAL NOT NULL,
  limit_price REAL,
  status TEXT NOT NULL,
  fill_price REAL,
  fill_qty REAL,
  fee REAL NOT NULL DEFAULT 0,
  signal_label_short TEXT,
  signal_score_short INTEGER,
  signal_label_long TEXT,
  signal_score_long INTEGER,
  triggered_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  filled_at TEXT,
  cancelled_at TEXT,
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_orders_account_status ON orders(account_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_ticker_status ON orders(ticker, status);

CREATE TABLE IF NOT EXISTS positions (
  account_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  qty REAL NOT NULL,
  avg_cost REAL NOT NULL,
  opened_at TEXT NOT NULL,
  PRIMARY KEY (account_id, ticker)
);

CREATE TABLE IF NOT EXISTS nav_history (
  account_id TEXT NOT NULL,
  date TEXT NOT NULL,
  cash REAL NOT NULL,
  market_value REAL NOT NULL,
  total_value REAL NOT NULL,
  PRIMARY KEY (account_id, date)
);
```

### 1.2 默认账户种子

`init_db` 末尾新增：若 `accounts` 中无 id=`default` 的行，则插入：
- id=`default`, type=`paper`, broker_adapter=`paper`, display_name=`默认虚拟账户`
- initial_cash=`settings.paper_initial_cash`（默认 100000）
- cash_balance=同 initial_cash, created_at=now ISO

### 1.3 models.py 追加 Pydantic 模型

```python
class AccountInfo(BaseModel):
    id: str
    type: str
    broker_adapter: str
    display_name: str
    initial_cash: float
    cash_balance: float
    created_at: str

class Position(BaseModel):
    account_id: str
    ticker: str
    qty: float
    avg_cost: float
    opened_at: str

class Order(BaseModel):
    id: str
    account_id: str
    ticker: str
    side: str            # 'buy' | 'sell'
    order_type: str      # 'market' | 'limit'
    qty: float
    limit_price: float | None
    status: str          # 'queued'|'pending'|'filled'|'cancelled'|'rejected'
    fill_price: float | None
    fill_qty: float | None
    fee: float
    signal_label_short: str | None
    signal_score_short: int | None
    signal_label_long: str | None
    signal_score_long: int | None
    triggered_by: str    # 'manual' | 'recommendation'
    created_at: str
    filled_at: str | None
    cancelled_at: str | None

class OrderRequest(BaseModel):
    ticker: str
    side: str
    order_type: str
    qty: float = Field(gt=0)
    limit_price: float | None = None
    triggered_by: str = "manual"

class NavPoint(BaseModel):
    date: str
    cash: float
    market_value: float
    total_value: float
```

### 1.4 config.py 追加

```python
paper_initial_cash: float = 100000.0
paper_fx_spread_pips: float = 0.5
```

### 测试（test_brokers_paper.py 中的一部分，先开 schema 测试）
- init_db 后 `accounts` 表存在并有 default 行
- cash_balance 等于 paper_initial_cash
- 重复 init_db 不会重置 cash_balance（INSERT OR IGNORE 行为）

**验收：** 测试通过；启动服务时观察日志确认默认账户存在。

---

## Task 2: BrokerAdapter 抽象接口（brokers/base.py）

**目标：** 定义统一的 broker 接口与异常类型，所有业务层只依赖此模块。

**新建文件：** `brokers/__init__.py`、`brokers/base.py`

### 接口定义

```python
from typing import Protocol, Literal
from models import AccountInfo, Position, Order, OrderRequest

class BrokerError(Exception): ...
class InsufficientFundsError(BrokerError): ...
class InsufficientPositionError(BrokerError): ...
class InvalidOrderError(BrokerError): ...
class OrderNotFoundError(BrokerError): ...
class MarketClosedError(BrokerError): ...   # 仅当未启用闭市排队时抛出

class BrokerAdapter(Protocol):
    name: str

    async def get_account(self, account_id: str) -> AccountInfo: ...
    async def get_positions(self, account_id: str) -> list[Position]: ...
    async def get_orders(
        self, account_id: str, status: str | None = None
    ) -> list[Order]: ...
    async def place_order(
        self,
        account_id: str,
        request: OrderRequest,
        signal_snapshot: dict | None,
    ) -> Order: ...
    async def cancel_order(self, account_id: str, order_id: str) -> Order: ...
```

`signal_snapshot` 形如 `{"label_short": ..., "score_short": ..., "label_long": ..., "score_long": ...}`，由调用方（router）从 `scan_results` 表或当时计算结果中获取后传入。

### 测试（test_brokers_paper.py 的 import 测试）
- 仅测试模块可导入、Protocol 类型存在；无运行时断言

**验收：** lint 通过、import 不报错。

---

## Task 3: PaperBrokerAdapter — 市价单核心逻辑

**目标：** 实装 paper adapter 的市价单买入/卖出，正确维护 cash_balance、positions、avg_cost。

**新建文件：** `brokers/paper.py`

**关键行为：**

### 买入市价单
1. 获取当前价（调用 `services.data_fetcher.fetch_ohlcv` 然后取最新 close；或直接复用 `scanner_service.scan_single` 提供的 current_price）。优先使用 `data_fetcher` 的 `fetch_current_price(ticker)` 辅助函数（若不存在则在此 task 加一个轻量包装）。
2. 计算总成本：`qty * fill_price + fee`（外汇按 `paper_fx_spread_pips` 在买入价上加点差）
3. 若 `cash_balance < 总成本` → 抛 `InsufficientFundsError`
4. 在事务中：扣减 cash_balance、upsert positions（avg_cost = (旧qty×旧avg + 新qty×新price) / 总qty）、写入 orders 行（status=`filled`）

### 卖出市价单
1. 检查 positions：若 qty < 卖出数量 → 抛 `InsufficientPositionError`
2. 在事务中：减少 positions.qty（若归零则 DELETE row）、增加 cash_balance（按卖出价 - fee）、写入 orders 行（status=`filled`）

### 闭市处理（先占位，下个 task 完成）
- 若市场闭市且 `order_type=market`：写入 status=`queued`，**不动 cash_balance / positions**；依赖 Task 5 的 matcher 释放

### TDD 测试要求（test_brokers_paper.py，必须先红再绿）
- 买入足够现金 → cash 减少，position 创建，order=filled
- 买入现金不足 → 抛错，DB 无变更
- 卖出有足够持仓 → position 减少，cash 增加，order=filled
- 卖出超出持仓 → 抛错，DB 无变更
- 二次买入同一标的 → avg_cost 按加权平均更新
- 卖空全部仓位 → positions 行被删除
- 外汇买入应用点差（fee>0），股票应用零佣金（fee=0）
- 多次买卖串行后，cash + Σ(qty×avg_cost) 与初始资金一致（不变量测试）

**测试中的价格获取**：使用 monkeypatch mock `fetch_current_price` 返回固定价格；不发真实网络请求。

**验收：** 全部测试通过。

---

## Task 4: 美股开闭市判定（services/market_hours.py）

**目标：** 提供 `is_us_market_open(now: datetime) -> bool` 与 `is_forex_market_open(now)`（永远 True，但显式建模）。

**简化规则（MVP 可接受）：**
- 美股开市：周一至周五，美东时间 09:30–16:00
- 不处理美国节假日（接受偶发误判；后期可接入 `pandas_market_calendars`）
- 时区转换通过 `zoneinfo.ZoneInfo("America/New_York")`

**辅助函数：**
- `should_queue_order(ticker: str, now: datetime) -> bool`：FX 永远 False；股票按市场开闭返回

### 测试（test_market_hours.py）
- 参数化时间点：周三 14:00 ET → True，周三 03:00 ET → False，周六中午 → False，周五 16:30 ET → False
- FX 任何时间 → True
- 时区边界：UTC 14:30（夏令时换算后 ET 10:30）→ True

**验收：** 测试覆盖典型边界。

---

## Task 5: 限价单与排队订单撮合（services/order_matcher.py）

**目标：** 在每轮扫描周期结束后调用，处理两类订单：
1. `queued` 美股订单 → 若市场已开 → 转 `pending` 后按当时市价成交（复用 paper adapter 的市价成交路径）
2. `pending` 限价单 → 若当前价穿越限价（buy: 当前价≤limit；sell: 当前价≥limit）→ 按 limit_price 成交

**接口：**
```python
async def match_open_orders(adapter: BrokerAdapter, current_prices: dict[str, float]) -> list[Order]:
    """current_prices 由扫描器在已 fetch 的 OHLCV 中取出后传入，避免重复网络请求。
    返回这一轮新撮合（filled/queued→filled）的订单列表。"""
```

**关键点：**
- 撮合应在事务里串行处理同一 ticker 的多张订单（避免 partial fill 竞争；MVP 简化为「足额或不动」）
- 撮合失败（如卖出时 position 不足）→ 标记 status=`rejected`，写入 cancelled_at
- 撮合成功的订单触发邮件通知（复用 `services.notifier.record_and_notify`，新增 alert_type=`order_filled`）

**集成到扫描器：**
- 修改 `services/scanner_service.run_full_scan`：扫描完信号后，从 scan 结果中聚合 `current_prices: dict`，调用 `match_open_orders(paper_adapter, current_prices)`

### 测试（test_order_matcher.py）
- 限价买单，当前价 ≤ 限价 → 成交，cash 扣减
- 限价买单，当前价 > 限价 → 仍 pending
- 限价卖单，当前价 ≥ 限价 → 成交
- queued 市价单，市场仍闭 → 仍 queued
- queued 市价单，市场已开 → 按当前价成交
- 卖出限价单触发但持仓不足 → status=rejected，position 不变
- 不变量：撮合前后 cash + 持仓市值 在每个账户上守恒（容差 ≤ 1e-6）

**验收：** 全部测试通过 + 在 scanner_service 测试中确认 matcher 被调用。

---

## Task 6: NAV 快照服务（services/nav_service.py）

**目标：** 每日收盘后写入一行 nav_history，记录账户净值。

**接口：**
```python
async def snapshot_nav(account_id: str, current_prices: dict[str, float]) -> NavPoint:
    """计算账户当前 cash + 持仓市值，写入 nav_history（INSERT OR REPLACE 当天行）。"""
```

**集成：**
- 在 `scheduler.py` 中新增一个 cron job：`day_of_week="mon-fri", hour=21, minute=30`（晚于 21:05 扫描）
- 该 job 内部 fetch 持仓涉及的所有 ticker 的当前价，然后调用 snapshot_nav

### 测试（test_nav_service.py）
- 单笔买入后 snapshot_nav → market_value = qty×current_price，total_value = cash + market_value
- 同一天调用两次 → 第二次覆盖（INSERT OR REPLACE 行为）
- 无持仓 → market_value = 0，total_value = cash

**验收：** 测试通过；scheduler 测试用 freezegun 验证 cron 触发时间正确。

---

## Task 7: Portfolio API 路由（routers/portfolio.py）

**目标：** 暴露虚拟交易 HTTP API，所有端点要求 JWT。

**端点：**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/portfolio/accounts` | 列出所有账户（MVP 只有一个 default） |
| GET | `/portfolio/accounts/{id}` | 单账户详情（含 cash_balance） |
| GET | `/portfolio/accounts/{id}/positions` | 当前持仓（含每标的当前价 + 浮动盈亏） |
| GET | `/portfolio/accounts/{id}/orders` | 订单列表，支持 `?status=filled&side=buy&limit=50` |
| POST | `/portfolio/accounts/{id}/orders` | 下单；body=OrderRequest，**自动从 scan_results 取最新信号快照**注入 |
| DELETE | `/portfolio/accounts/{id}/orders/{order_id}` | 取消订单（仅 queued/pending） |
| GET | `/portfolio/accounts/{id}/nav-history?days=90` | NAV 序列 |
| GET | `/portfolio/accounts/{id}/performance` | 汇总：总收益率、累计盈亏、按信号分类的胜率（基于 filled+已平仓订单） |

**信号快照取数逻辑（在 POST 端点内）：**
1. 查询 `scan_results` 表中该 ticker 最近一行
2. 抽出 short/long 的 label 与 score
3. 若无记录（机会发现尚未跑过），signal_*字段全 None

**异常映射：**
- `InsufficientFundsError` → 400 「现金不足」
- `InsufficientPositionError` → 400 「持仓不足」
- `InvalidOrderError` → 400
- `OrderNotFoundError` → 404
- `MarketClosedError` → 不会抛出（MVP 总是排队），保留映射以防未来配置关闭排队

### 测试（test_routers_portfolio.py）
- 未登录 → 401
- 已登录 + GET accounts → 返回 default 账户
- POST 市价买单 → 201，返回 order with status=filled（mock 价格、mock market_open=True）
- POST 闭市买单 → 201，order status=queued
- POST 现金不足 → 400
- DELETE 已成交订单 → 400
- DELETE pending 限价单 → 200
- GET orders 过滤 status → 仅返回匹配项
- GET performance 在零订单时返回零值，不报错

**验收：** 测试全过；手动用 curl 跑通一次买卖循环。

---

## Task 8: 扫描器集成 + 通知集成 + 路由挂载

**目标：** 把前面构件接进现有系统的运行链路。

**修改文件：** `main.py`、`services/scanner_service.py`、`services/scheduler.py`、`services/notifier.py`

### 8.1 main.py
- `app.include_router(portfolio.router)`
- lifespan 中初始化全局 `paper_adapter = PaperBrokerAdapter(...)` 实例（或 dependency-injection via FastAPI Depends）

### 8.2 scanner_service.run_full_scan
- 扫描循环内累积 `current_prices: dict[str, float]`
- 循环结束后调用 `match_open_orders(paper_adapter, current_prices)`
- 撮合的每张 filled 订单调用 `notifier.notify_order_filled(order)`

### 8.3 scheduler.py
- 新增 daily NAV 快照 cron job（见 Task 6）

### 8.4 notifier.py
- 新增 `notify_order_filled(order: Order)`：写 alert_history（alert_type=`order_filled`）+ 邮件通知
- 邮件模板：「您的订单 {ticker} {side} {qty} @ {fill_price} 已成交」

### 测试
- 端到端：mock data_fetcher → run_full_scan 触发已挂限价单成交 → alert_history 中出现 order_filled 行
- scheduler 启动后包含 3 个 cron job（stock_scan, fx_scan, nav_snapshot）

**验收：** 端到端测试通过；启动服务后日志显示 3 个 scheduler job。

---

## Task 9: 全量回归与文档

**目标：** 确认 Plan 1 的现有测试全部仍然通过，并简单更新 README（如有）。

**步骤：**
1. `pytest -q` 全跑（应至少 55 + 新增约 35 = 90+ 测试）
2. 启动 `uvicorn main:app --reload`，curl 验证：
   - GET /portfolio/accounts → 默认账户
   - POST 买入 AAPL 10 股 → 成交
   - GET /portfolio/accounts/default/positions → AAPL qty=10
   - POST 限价卖单 → pending
   - DELETE 限价单 → cancelled
3. 检查 `data.db` 的 4 张新表均有正确 schema（`sqlite3 data.db .schema`）
4. 在 git 中产出干净的提交序列（每个 task 一次或多次原子提交）

**验收：** 全部测试通过；手动验证清单全过；提交干净。

---

## 风险与回退点

| 风险 | 缓解 |
|---|---|
| `data_fetcher` 没有「仅取当前价」的轻量函数 | Task 3 中加一个 `fetch_current_price(ticker)`，复用 query2 链路 |
| 扫描器集成 matcher 后变慢 | 撮合只走 DB，无网络；可接受 |
| 限价单浮点精度问题 | 用 `pytest.approx(rel=1e-6)`；DB 存 REAL 已足够 MVP |
| 美股节假日误判 | 接受；后期接 `pandas_market_calendars` |
| 多次启动 init_db 重置默认账户 cash | 用 `INSERT OR IGNORE`；测试覆盖 |
| Task 7 的 signal 快照查询慢 | scan_results 已按 ticker 索引；MVP 量级可接受 |

---

## 后续（不在本计划内）

- 前端持仓/下单/历史 UI（在 Plan 2 追加任务）
- 性能页扩展为完整回测页
- 真实经纪商 adapter（Alpaca/IB）
- MCP server 子包
- 止损订单
