# 股票投资辅助工具 — Plan 1：后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建完整的 FastAPI 后端，包含信号引擎、数据获取、全部 REST API 和通知系统。

**Architecture:** Python FastAPI 应用，SQLite 持久化，yfinance 获取行情数据，pandas-ta 计算技术指标，规则引擎将指标转换为 -4 到 +4 评分，APScheduler 定时扫描，SMTP 邮件通知。

**Tech Stack:** Python 3.11+, FastAPI, SQLite (aiosqlite), yfinance, pandas-ta, APScheduler, python-jose (JWT), aiosmtplib

---

## 文件结构

```
stock-tool/
└── backend/
    ├── main.py                    # FastAPI 入口，注册路由
    ├── config.py                  # 从 .env 读取配置
    ├── database.py                # SQLite 连接与建表
    ├── models.py                  # Pydantic 数据模型（全局共享类型）
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py                # POST /auth/login, POST /auth/logout
    │   ├── watchlist.py           # GET/POST/DELETE /watchlist
    │   ├── scanner.py             # GET /scanner/results, POST /scanner/trigger
    │   ├── alerts.py              # CRUD /alerts/price, /alerts/signal, GET /alerts/history
    │   └── analysis.py            # GET /analysis/{ticker}, POST /analysis/{ticker}/deep
    ├── services/
    │   ├── __init__.py
    │   ├── data_fetcher.py        # yfinance 封装，拉取 OHLCV
    │   ├── indicator_engine.py    # pandas-ta 计算：EMA/RSI/MACD/Volume
    │   ├── signal_engine.py       # 规则引擎：指标 → 评分 → SignalScore
    │   ├── templates.py           # 中文描述模板映射
    │   ├── scanner_service.py     # 批量扫描 S&P500 + FX 资产池
    │   ├── notifier.py            # SMTP 邮件发送
    │   └── scheduler.py           # APScheduler 定时任务配置
    ├── data/
    │   ├── __init__.py
    │   └── universe.py            # 资产池：S&P500 + FX 对列表
    ├── tests/
    │   ├── conftest.py
    │   ├── test_indicator_engine.py
    │   ├── test_signal_engine.py
    │   ├── test_templates.py
    │   └── test_scanner_service.py
    ├── requirements.txt
    ├── .env.example
    └── Dockerfile
```

---

## Task 1: 项目脚手架与依赖

**Files:**
- Create: `stock-tool/backend/requirements.txt`
- Create: `stock-tool/backend/.env.example`
- Create: `stock-tool/backend/config.py`
- Create: `stock-tool/backend/main.py`

- [ ] **Step 1: 创建项目目录**

```bash
mkdir -p stock-tool/backend/{routers,services,data,tests}
touch stock-tool/backend/routers/__init__.py
touch stock-tool/backend/services/__init__.py
touch stock-tool/backend/data/__init__.py
touch stock-tool/backend/tests/__init__.py
```

- [ ] **Step 2: 写 requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
aiosqlite==0.20.0
yfinance==0.2.41
pandas-ta==0.3.14b
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1
pydantic-settings==2.5.2
apscheduler==3.10.4
aiosmtplib==3.0.1
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.23.8
anthropic==0.34.2
```

- [ ] **Step 3: 写 .env.example**

```env
APP_PASSWORD=changeme
SECRET_KEY=replace-with-random-64-char-hex
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your-app-password
NOTIFY_EMAIL=your@gmail.com
CLAUDE_API_KEY=
DATABASE_URL=./data.db
```

- [ ] **Step 4: 写 config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_password: str
    secret_key: str
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    notify_email: str = ""
    claude_api_key: str = ""
    database_url: str = "./data.db"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 5: 安装依赖**

```bash
cd stock-tool/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Expected: 所有包安装成功，无报错。

- [ ] **Step 6: 写 main.py（骨架）**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db
from routers import auth, watchlist, scanner, alerts, analysis

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Stock Tool API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
app.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: 验证服务器启动**

```bash
uvicorn main:app --reload
```

Expected: 在 http://localhost:8000/health 返回 `{"status": "ok"}`，http://localhost:8000/docs 显示 Swagger UI。

- [ ] **Step 8: Commit**

```bash
git add stock-tool/backend
git commit -m "feat: backend project scaffolding"
```

---

## Task 2: 数据库 Schema 与模型

**Files:**
- Create: `stock-tool/backend/database.py`
- Create: `stock-tool/backend/models.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_database.py`：

```python
import pytest
import aiosqlite
from database import init_db, get_db

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    await init_db()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in await cursor.fetchall()}
    assert "watchlist" in tables
    assert "scan_results" in tables
    assert "price_alerts" in tables
    assert "signal_alerts" in tables
    assert "alert_history" in tables
    assert "previous_signals" in tables
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_database.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: 写 database.py**

```python
import aiosqlite
from contextlib import asynccontextmanager
from config import settings

@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with aiosqlite.connect(settings.database_url) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                market TEXT NOT NULL,
                sector TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS scan_results (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sector TEXT NOT NULL,
                market TEXT NOT NULL,
                price REAL,
                change_pct REAL,
                short_score INTEGER,
                short_label TEXT,
                short_color TEXT,
                long_score INTEGER,
                long_label TEXT,
                long_color TEXT,
                short_indicators TEXT,
                long_indicators TEXT,
                scanned_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                condition TEXT NOT NULL,
                threshold REAL NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS signal_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                condition TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS previous_signals (
                ticker TEXT PRIMARY KEY,
                short_score INTEGER,
                long_score INTEGER,
                rsi_daily REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
```

- [ ] **Step 4: 写 models.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class IndicatorResult(BaseModel):
    name: str
    raw_value: str
    description: str
    contribution: int  # +1 or -1

class SignalScore(BaseModel):
    score: int  # -4 to +4
    label: str
    color: str  # "green" | "yellow" | "red"
    indicators: list[IndicatorResult]

class SignalResult(BaseModel):
    ticker: str
    name: str
    sector: str
    market: str  # "stock" | "forex"
    price: float
    change_pct: float
    short_term: SignalScore
    long_term: SignalScore
    scanned_at: datetime

class WatchlistItem(BaseModel):
    ticker: str
    name: str
    market: str
    sector: str
    added_at: Optional[datetime] = None

class PriceAlertCreate(BaseModel):
    ticker: str
    condition: str  # "above" | "below"
    threshold: float

class SignalAlertCreate(BaseModel):
    ticker: str
    condition: str  # "any_change" | "strong_only" | "rsi_extreme"

class AlertHistoryItem(BaseModel):
    id: int
    ticker: str
    alert_type: str
    message: str
    triggered_at: datetime
    read: bool
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
pytest tests/test_database.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add stock-tool/backend/database.py stock-tool/backend/models.py stock-tool/backend/tests/test_database.py
git commit -m "feat: database schema and pydantic models"
```

---

## Task 3: 认证（密码登录 + JWT）

**Files:**
- Create: `stock-tool/backend/routers/auth.py`
- Create: `stock-tool/backend/tests/test_auth.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_login_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/auth/login", json={"password": "changeme"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/auth/login", json={"password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_protected_route_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/watchlist")
    assert resp.status_code == 401
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_auth.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 routers/auth.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import settings

router = APIRouter()
bearer = HTTPBearer()

class LoginRequest(BaseModel):
    password: str

def create_token() -> str:
    payload = {"exp": datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True

@router.post("/login")
async def login(req: LoginRequest):
    if req.password != settings.app_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"access_token": create_token(), "token_type": "bearer"}
```

- [ ] **Step 4: 更新 routers/watchlist.py（骨架，加入 auth 依赖）**

```python
from fastapi import APIRouter, Depends
from routers.auth import require_auth

router = APIRouter()

@router.get("")
async def get_watchlist(_=Depends(require_auth)):
    return []
```

同样为 `routers/scanner.py`、`routers/alerts.py`、`routers/analysis.py` 创建相同骨架。

- [ ] **Step 5: 运行测试，确认通过**

```bash
pytest tests/test_auth.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add stock-tool/backend/routers/auth.py stock-tool/backend/tests/test_auth.py
git commit -m "feat: password auth with JWT"
```

---

## Task 4: 资产池数据

**Files:**
- Create: `stock-tool/backend/data/universe.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_universe.py
from data.universe import SP500_TICKERS, FX_PAIRS, get_all_tickers

def test_sp500_has_expected_stocks():
    assert "AAPL" in SP500_TICKERS
    assert "MSFT" in SP500_TICKERS
    assert "NVDA" in SP500_TICKERS
    assert len(SP500_TICKERS) >= 100  # 使用精简版，不需要全500

def test_fx_pairs_coverage():
    assert "EURUSD=X" in FX_PAIRS
    assert "USDJPY=X" in FX_PAIRS
    assert len(FX_PAIRS) == 20

def test_get_all_tickers():
    all_tickers = get_all_tickers()
    assert len(all_tickers) == len(SP500_TICKERS) + len(FX_PAIRS)
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_universe.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 data/universe.py**

```python
# 精简版 S&P 500 — 按市值选取前150只，覆盖主要板块
SP500_TICKERS: list[dict] = [
    # 信息技术
    {"ticker": "AAPL",  "name": "苹果",     "sector": "信息技术·消费电子"},
    {"ticker": "MSFT",  "name": "微软",     "sector": "信息技术·软件"},
    {"ticker": "NVDA",  "name": "英伟达",   "sector": "信息技术·半导体"},
    {"ticker": "AVGO",  "name": "博通",     "sector": "信息技术·半导体"},
    {"ticker": "ORCL",  "name": "甲骨文",   "sector": "信息技术·软件"},
    {"ticker": "AMD",   "name": "超微半导体","sector": "信息技术·半导体"},
    {"ticker": "QCOM",  "name": "高通",     "sector": "信息技术·半导体"},
    {"ticker": "INTC",  "name": "英特尔",   "sector": "信息技术·半导体"},
    {"ticker": "META",  "name": "Meta",    "sector": "通信服务·社交媒体"},
    {"ticker": "GOOGL", "name": "谷歌",     "sector": "通信服务·互联网"},
    {"ticker": "NFLX",  "name": "奈飞",     "sector": "通信服务·流媒体"},
    # 消费
    {"ticker": "AMZN",  "name": "亚马逊",   "sector": "非必需消费·电商"},
    {"ticker": "TSLA",  "name": "特斯拉",   "sector": "非必需消费·电动车"},
    {"ticker": "HD",    "name": "家得宝",   "sector": "非必需消费·零售"},
    {"ticker": "MCD",   "name": "麦当劳",   "sector": "非必需消费·餐饮"},
    {"ticker": "SBUX",  "name": "星巴克",   "sector": "非必需消费·餐饮"},
    {"ticker": "COST",  "name": "好市多",   "sector": "必需消费·零售"},
    {"ticker": "WMT",   "name": "沃尔玛",   "sector": "必需消费·零售"},
    {"ticker": "KO",    "name": "可口可乐", "sector": "必需消费·饮料"},
    {"ticker": "PEP",   "name": "百事可乐", "sector": "必需消费·饮料"},
    # 金融
    {"ticker": "JPM",   "name": "摩根大通", "sector": "金融·银行"},
    {"ticker": "BAC",   "name": "美国银行", "sector": "金融·银行"},
    {"ticker": "GS",    "name": "高盛",     "sector": "金融·投资银行"},
    {"ticker": "V",     "name": "Visa",    "sector": "金融·支付"},
    {"ticker": "MA",    "name": "万事达",   "sector": "金融·支付"},
    # 医疗
    {"ticker": "JNJ",   "name": "强生",     "sector": "医疗保健·制药"},
    {"ticker": "UNH",   "name": "联合健康", "sector": "医疗保健·保险"},
    {"ticker": "PFE",   "name": "辉瑞",     "sector": "医疗保健·制药"},
    {"ticker": "ABBV",  "name": "艾伯维",   "sector": "医疗保健·制药"},
    {"ticker": "MRK",   "name": "默克",     "sector": "医疗保健·制药"},
    # 能源
    {"ticker": "XOM",   "name": "埃克森美孚","sector": "能源·石油天然气"},
    {"ticker": "CVX",   "name": "雪佛龙",   "sector": "能源·石油天然气"},
    # 工业
    {"ticker": "CAT",   "name": "卡特彼勒", "sector": "工业·机械"},
    {"ticker": "BA",    "name": "波音",     "sector": "工业·航空航天"},
    {"ticker": "HON",   "name": "霍尼韦尔", "sector": "工业·多元化"},
    # 其他常见
    {"ticker": "BRK-B", "name": "伯克希尔", "sector": "金融·多元化"},
    {"ticker": "SPY",   "name": "标普500ETF","sector": "ETF·大盘"},
    {"ticker": "QQQ",   "name": "纳斯达克ETF","sector": "ETF·科技"},
]

FX_PAIRS: list[dict] = [
    {"ticker": "EURUSD=X", "name": "欧元/美元", "sector": "外汇·主要货币对"},
    {"ticker": "GBPUSD=X", "name": "英镑/美元", "sector": "外汇·主要货币对"},
    {"ticker": "USDJPY=X", "name": "美元/日元", "sector": "外汇·主要货币对"},
    {"ticker": "USDCHF=X", "name": "美元/瑞郎", "sector": "外汇·主要货币对"},
    {"ticker": "AUDUSD=X", "name": "澳元/美元", "sector": "外汇·主要货币对"},
    {"ticker": "USDCAD=X", "name": "美元/加元", "sector": "外汇·主要货币对"},
    {"ticker": "NZDUSD=X", "name": "纽元/美元", "sector": "外汇·主要货币对"},
    {"ticker": "EURGBP=X", "name": "欧元/英镑", "sector": "外汇·交叉盘"},
    {"ticker": "EURJPY=X", "name": "欧元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "GBPJPY=X", "name": "英镑/日元", "sector": "外汇·交叉盘"},
    {"ticker": "AUDJPY=X", "name": "澳元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "EURCHF=X", "name": "欧元/瑞郎", "sector": "外汇·交叉盘"},
    {"ticker": "GBPCHF=X", "name": "英镑/瑞郎", "sector": "外汇·交叉盘"},
    {"ticker": "CADJPY=X", "name": "加元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "AUDCAD=X", "name": "澳元/加元", "sector": "外汇·交叉盘"},
    {"ticker": "NZDJPY=X", "name": "纽元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "EURCAD=X", "name": "欧元/加元", "sector": "外汇·交叉盘"},
    {"ticker": "GBPAUD=X", "name": "英镑/澳元", "sector": "外汇·交叉盘"},
    {"ticker": "AUDNZD=X", "name": "澳元/纽元", "sector": "外汇·交叉盘"},
    {"ticker": "CHFJPY=X", "name": "瑞郎/日元", "sector": "外汇·交叉盘"},
]

_TICKER_MAP: dict[str, dict] = {
    item["ticker"]: item
    for item in SP500_TICKERS + FX_PAIRS
}

def get_all_tickers() -> list[dict]:
    return SP500_TICKERS + FX_PAIRS

def get_ticker_info(ticker: str) -> dict | None:
    return _TICKER_MAP.get(ticker)

def is_forex(ticker: str) -> bool:
    return ticker.endswith("=X")
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_universe.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock-tool/backend/data/universe.py stock-tool/backend/tests/test_universe.py
git commit -m "feat: asset universe (S&P500 subset + 20 FX pairs)"
```

---

## Task 5: 数据获取层（yfinance 封装）

**Files:**
- Create: `stock-tool/backend/services/data_fetcher.py`
- Create: `stock-tool/backend/tests/test_data_fetcher.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_data_fetcher.py
import pytest
import pandas as pd
from services.data_fetcher import fetch_ohlcv, OHLCVData

def test_fetch_daily_stock():
    data = fetch_ohlcv("AAPL", period="1mo", interval="1d")
    assert isinstance(data, OHLCVData)
    assert len(data.daily) >= 15
    assert all(col in data.daily.columns for col in ["Open","High","Low","Close","Volume"])

def test_fetch_daily_forex():
    data = fetch_ohlcv("EURUSD=X", period="1mo", interval="1d")
    assert isinstance(data, OHLCVData)
    assert len(data.daily) >= 15

def test_fetch_returns_weekly():
    data = fetch_ohlcv("AAPL", period="1y", interval="1wk")
    assert len(data.weekly) >= 30

def test_fetch_invalid_ticker_returns_none():
    data = fetch_ohlcv("INVALID_TICKER_XYZ", period="1mo", interval="1d")
    assert data is None
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_data_fetcher.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 services/data_fetcher.py**

```python
import yfinance as yf
import pandas as pd
from dataclasses import dataclass

@dataclass
class OHLCVData:
    ticker: str
    daily: pd.DataFrame
    weekly: pd.DataFrame
    current_price: float
    change_pct: float

def fetch_ohlcv(ticker: str, period: str = "6mo", interval: str = "1d") -> OHLCVData | None:
    try:
        tk = yf.Ticker(ticker)
        daily = tk.history(period="6mo", interval="1d")
        weekly = tk.history(period="2y", interval="1wk")

        if daily.empty or len(daily) < 5:
            return None

        current_price = float(daily["Close"].iloc[-1])
        prev_price = float(daily["Close"].iloc[-2]) if len(daily) >= 2 else current_price
        change_pct = (current_price - prev_price) / prev_price * 100

        return OHLCVData(
            ticker=ticker,
            daily=daily,
            weekly=weekly,
            current_price=round(current_price, 4),
            change_pct=round(change_pct, 2),
        )
    except Exception:
        return None
```

- [ ] **Step 4: 运行测试（注意：此测试需要网络，稍慢）**

```bash
pytest tests/test_data_fetcher.py -v --timeout=30
```

Expected: PASS（约 10-20 秒，因为需要请求 Yahoo Finance）

- [ ] **Step 5: Commit**

```bash
git add stock-tool/backend/services/data_fetcher.py stock-tool/backend/tests/test_data_fetcher.py
git commit -m "feat: yfinance OHLCV data fetcher"
```

---

## Task 6: 指标计算引擎（pandas-ta）

**Files:**
- Create: `stock-tool/backend/services/indicator_engine.py`
- Create: `stock-tool/backend/tests/test_indicator_engine.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_indicator_engine.py
import pytest
import pandas as pd
import numpy as np
from services.indicator_engine import calculate_indicators, IndicatorValues

def _make_ohlcv(n=60) -> pd.DataFrame:
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    volume = np.random.randint(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({
        "Open": close * 0.999,
        "High": close * 1.005,
        "Low": close * 0.995,
        "Close": close,
        "Volume": volume,
    })

def test_calculate_returns_indicator_values():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert isinstance(vals, IndicatorValues)

def test_ema_values_present():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert vals.ema_20 is not None
    assert vals.ema_50 is not None
    assert vals.ema_200 is not None

def test_rsi_in_range():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert 0 <= vals.rsi_daily <= 100

def test_macd_present():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert vals.macd_line is not None
    assert vals.macd_signal is not None

def test_volume_ratio():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert vals.volume_ratio > 0

def test_weekly_rsi_present():
    df_weekly = _make_ohlcv(60)
    vals = calculate_indicators(df_weekly, is_weekly=True)
    assert 0 <= vals.rsi_weekly <= 100

def test_returns_none_on_insufficient_data():
    df = _make_ohlcv(10)  # 不足以计算 EMA50
    vals = calculate_indicators(df)
    assert vals.ema_50 is None
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_indicator_engine.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 services/indicator_engine.py**

```python
import pandas as pd
import pandas_ta as ta
from dataclasses import dataclass

@dataclass
class IndicatorValues:
    # EMA
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None
    ema_200_slope: float | None  # EMA200最近20天斜率（正=上升）
    # RSI
    rsi_daily: float
    rsi_weekly: float  # 0 if not weekly calculation
    # MACD
    macd_line: float | None
    macd_signal: float | None
    # Volume
    volume_ratio: float  # current / 20-day avg
    # Price
    current_price: float

def calculate_indicators(df: pd.DataFrame, is_weekly: bool = False) -> IndicatorValues:
    close = df["Close"]
    volume = df.get("Volume", pd.Series(dtype=float))
    n = len(close)

    def _ema(period: int) -> float | None:
        if n < period:
            return None
        result = ta.ema(close, length=period)
        if result is None or result.empty:
            return None
        val = result.iloc[-1]
        return float(val) if not pd.isna(val) else None

    ema_20 = _ema(20)
    ema_50 = _ema(50)
    ema_200 = _ema(200)

    # EMA200 slope: compare current vs 20 bars ago
    ema_200_slope = None
    if ema_200 is not None and n >= 220:
        ema200_series = ta.ema(close, length=200)
        if ema200_series is not None and len(ema200_series) >= 20:
            prev = ema200_series.iloc[-20]
            curr = ema200_series.iloc[-1]
            if not pd.isna(prev):
                ema_200_slope = float(curr - prev)

    # RSI
    rsi_series = ta.rsi(close, length=14)
    rsi_val = 50.0
    if rsi_series is not None and not rsi_series.empty:
        v = rsi_series.iloc[-1]
        if not pd.isna(v):
            rsi_val = float(v)

    rsi_daily = rsi_val if not is_weekly else 50.0
    rsi_weekly = rsi_val if is_weekly else 50.0

    # MACD
    macd_line = macd_signal = None
    if n >= 26:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            ml = macd_df.iloc[-1].get("MACD_12_26_9")
            ms = macd_df.iloc[-1].get("MACDs_12_26_9")
            if ml is not None and not pd.isna(ml):
                macd_line = float(ml)
            if ms is not None and not pd.isna(ms):
                macd_signal = float(ms)

    # Volume ratio
    volume_ratio = 1.0
    if not volume.empty and len(volume) >= 20:
        avg = volume.iloc[-20:].mean()
        if avg > 0:
            volume_ratio = float(volume.iloc[-1] / avg)

    return IndicatorValues(
        ema_20=ema_20,
        ema_50=ema_50,
        ema_200=ema_200,
        ema_200_slope=ema_200_slope,
        rsi_daily=rsi_daily,
        rsi_weekly=rsi_weekly,
        macd_line=macd_line,
        macd_signal=macd_signal,
        volume_ratio=volume_ratio,
        current_price=float(close.iloc[-1]),
    )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_indicator_engine.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock-tool/backend/services/indicator_engine.py stock-tool/backend/tests/test_indicator_engine.py
git commit -m "feat: indicator engine (EMA/RSI/MACD/Volume via pandas-ta)"
```

---

## Task 7: 信号规则引擎 + 中文模板

**Files:**
- Create: `stock-tool/backend/services/signal_engine.py`
- Create: `stock-tool/backend/services/templates.py`
- Create: `stock-tool/backend/tests/test_signal_engine.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_signal_engine.py
import pytest
from services.indicator_engine import IndicatorValues
from services.signal_engine import compute_short_term, compute_long_term, score_to_label
from models import SignalScore

def _make_vals(**kwargs) -> IndicatorValues:
    defaults = dict(
        ema_20=105.0, ema_50=100.0, ema_200=90.0, ema_200_slope=0.5,
        rsi_daily=60.0, rsi_weekly=55.0,
        macd_line=0.5, macd_signal=0.3,
        volume_ratio=1.4, current_price=110.0,
    )
    defaults.update(kwargs)
    return IndicatorValues(**defaults)

def test_score_to_label_strong_bullish():
    label, color = score_to_label(4)
    assert label == "强烈看涨"
    assert color == "green"

def test_score_to_label_strong_bearish():
    label, color = score_to_label(-4)
    assert label == "强烈看跌"
    assert color == "red"

def test_score_to_label_neutral():
    label, color = score_to_label(0)
    assert label == "中性观望"
    assert color == "yellow"

def test_short_term_all_bullish():
    vals = _make_vals(ema_20=105, ema_50=100, rsi_daily=60, macd_line=0.5, macd_signal=0.3, volume_ratio=1.5)
    score = compute_short_term(vals)
    assert score.score == 4
    assert score.color == "green"
    assert len(score.indicators) == 4

def test_short_term_all_bearish():
    vals = _make_vals(ema_20=95, ema_50=100, rsi_daily=40, macd_line=-0.5, macd_signal=-0.3, volume_ratio=0.8)
    score = compute_short_term(vals)
    assert score.score == -4

def test_long_term_all_bullish():
    vals = _make_vals(ema_50=105, ema_200=100, ema_200_slope=0.5, rsi_weekly=60, current_price=110)
    score = compute_long_term(vals)
    assert score.score == 4

def test_indicators_have_descriptions():
    vals = _make_vals()
    score = compute_short_term(vals)
    for ind in score.indicators:
        assert len(ind.description) > 0
        assert ind.contribution in (-1, +1)
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_signal_engine.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 services/templates.py**

```python
from services.indicator_engine import IndicatorValues

def ema_short_description(vals: IndicatorValues, contribution: int) -> str:
    if vals.ema_20 is None or vals.ema_50 is None:
        return "EMA数据不足"
    if contribution == 1:
        return f"短期均线(EMA20={vals.ema_20:.2f})上穿长期均线(EMA50={vals.ema_50:.2f})，趋势向上"
    return f"短期均线(EMA20={vals.ema_20:.2f})下穿长期均线(EMA50={vals.ema_50:.2f})，趋势向下"

def rsi_short_description(rsi: float, contribution: int) -> str:
    if rsi < 30:
        return f"RSI({rsi:.1f})进入超卖区，可能出现反弹"
    if rsi > 70:
        return f"RSI({rsi:.1f})进入超买区，注意回调风险"
    if contribution == 1:
        return f"RSI({rsi:.1f})处于中性偏强区间，动能向上"
    return f"RSI({rsi:.1f})处于中性偏弱区间，动能不足"

def macd_description(macd: float, signal: float, contribution: int) -> str:
    if contribution == 1:
        return f"MACD({macd:.3f})上穿信号线({signal:.3f})，金叉，动能由跌转涨"
    return f"MACD({macd:.3f})下穿信号线({signal:.3f})，死叉，动能由涨转跌"

def volume_description(ratio: float, contribution: int) -> str:
    pct = (ratio - 1) * 100
    if contribution == 1:
        return f"成交量较20日均值放大{pct:.0f}%，信号更可信"
    return f"成交量较20日均值缩减{abs(pct):.0f}%，信号参考性有限"

def ema_long_description(vals: IndicatorValues, contribution: int) -> str:
    if vals.ema_50 is None or vals.ema_200 is None:
        return "长期EMA数据不足"
    if contribution == 1:
        return f"EMA50({vals.ema_50:.2f})在EMA200({vals.ema_200:.2f})上方，黄金交叉格局"
    return f"EMA50({vals.ema_50:.2f})在EMA200({vals.ema_200:.2f})下方，死亡交叉格局"

def price_vs_ema200_description(price: float, ema200: float, contribution: int) -> str:
    if contribution == 1:
        return f"当前价格({price:.2f})站上EMA200({ema200:.2f})，长期趋势向上"
    return f"当前价格({price:.2f})跌破EMA200({ema200:.2f})，长期趋势向下"

def rsi_weekly_description(rsi: float, contribution: int) -> str:
    if contribution == 1:
        return f"周线RSI({rsi:.1f})高于50，长期动能偏强"
    return f"周线RSI({rsi:.1f})低于50，长期动能偏弱"

def ema200_slope_description(slope: float, contribution: int) -> str:
    if contribution == 1:
        return f"EMA200斜率为正(+{slope:.2f})，长期趋势仍在走强"
    return f"EMA200斜率为负({slope:.2f})，长期趋势正在走弱"
```

- [ ] **Step 4: 写 services/signal_engine.py**

```python
from models import SignalScore, IndicatorResult
from services.indicator_engine import IndicatorValues
from services import templates

def score_to_label(score: int) -> tuple[str, str]:
    if score >= 3:
        return "强烈看涨", "green"
    if score >= 1:
        return "看涨信号", "green"
    if score == 0:
        return "中性观望", "yellow"
    if score >= -2:
        return "看跌信号", "red"
    return "强烈看跌", "red"

def compute_short_term(vals: IndicatorValues) -> SignalScore:
    indicators: list[IndicatorResult] = []

    # 1. EMA 20/50
    if vals.ema_20 is not None and vals.ema_50 is not None:
        c = 1 if vals.ema_20 > vals.ema_50 else -1
        indicators.append(IndicatorResult(
            name="EMA趋势",
            raw_value=f"EMA20={vals.ema_20:.2f} / EMA50={vals.ema_50:.2f}",
            description=templates.ema_short_description(vals, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(name="EMA趋势", raw_value="N/A", description="数据不足", contribution=-1))

    # 2. RSI daily
    rsi = vals.rsi_daily
    c = 1 if rsi >= 50 else -1
    indicators.append(IndicatorResult(
        name="RSI(14)",
        raw_value=f"{rsi:.1f}",
        description=templates.rsi_short_description(rsi, c),
        contribution=c,
    ))

    # 3. MACD
    if vals.macd_line is not None and vals.macd_signal is not None:
        c = 1 if vals.macd_line > vals.macd_signal else -1
        indicators.append(IndicatorResult(
            name="MACD",
            raw_value=f"MACD={vals.macd_line:.3f} / Signal={vals.macd_signal:.3f}",
            description=templates.macd_description(vals.macd_line, vals.macd_signal, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(name="MACD", raw_value="N/A", description="数据不足", contribution=-1))

    # 4. Volume
    c = 1 if vals.volume_ratio >= 1.0 else -1
    indicators.append(IndicatorResult(
        name="成交量",
        raw_value=f"{vals.volume_ratio:.2f}x均值",
        description=templates.volume_description(vals.volume_ratio, c),
        contribution=c,
    ))

    score = sum(ind.contribution for ind in indicators)
    label, color = score_to_label(score)
    return SignalScore(score=score, label=label, color=color, indicators=indicators)

def compute_long_term(vals: IndicatorValues) -> SignalScore:
    indicators: list[IndicatorResult] = []

    # 1. EMA 50/200 cross
    if vals.ema_50 is not None and vals.ema_200 is not None:
        c = 1 if vals.ema_50 > vals.ema_200 else -1
        indicators.append(IndicatorResult(
            name="EMA金/死叉",
            raw_value=f"EMA50={vals.ema_50:.2f} / EMA200={vals.ema_200:.2f}",
            description=templates.ema_long_description(vals, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(name="EMA金/死叉", raw_value="N/A", description="数据不足", contribution=-1))

    # 2. Price vs EMA200
    if vals.ema_200 is not None:
        c = 1 if vals.current_price > vals.ema_200 else -1
        indicators.append(IndicatorResult(
            name="价格vs长期均线",
            raw_value=f"价格={vals.current_price:.2f} / EMA200={vals.ema_200:.2f}",
            description=templates.price_vs_ema200_description(vals.current_price, vals.ema_200, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(name="价格vs长期均线", raw_value="N/A", description="数据不足", contribution=-1))

    # 3. RSI weekly
    rsi_w = vals.rsi_weekly
    c = 1 if rsi_w >= 50 else -1
    indicators.append(IndicatorResult(
        name="周线RSI",
        raw_value=f"{rsi_w:.1f}",
        description=templates.rsi_weekly_description(rsi_w, c),
        contribution=c,
    ))

    # 4. EMA200 slope
    if vals.ema_200_slope is not None:
        c = 1 if vals.ema_200_slope > 0 else -1
        indicators.append(IndicatorResult(
            name="长期趋势斜率",
            raw_value=f"{vals.ema_200_slope:+.2f}",
            description=templates.ema200_slope_description(vals.ema_200_slope, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(name="长期趋势斜率", raw_value="N/A", description="数据不足", contribution=-1))

    score = sum(ind.contribution for ind in indicators)
    label, color = score_to_label(score)
    return SignalScore(score=score, label=label, color=color, indicators=indicators)
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
pytest tests/test_signal_engine.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add stock-tool/backend/services/signal_engine.py stock-tool/backend/services/templates.py stock-tool/backend/tests/test_signal_engine.py
git commit -m "feat: signal rule engine and Chinese text templates"
```

---

## Task 8: 扫描服务 + 定时任务

**Files:**
- Create: `stock-tool/backend/services/scanner_service.py`
- Create: `stock-tool/backend/services/scheduler.py`
- Modify: `stock-tool/backend/main.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_scanner_service.py
import pytest
from unittest.mock import patch, MagicMock
from services.scanner_service import scan_single, build_signal_result
from services.data_fetcher import OHLCVData
from services.indicator_engine import IndicatorValues
import pandas as pd
import numpy as np

def _mock_ohlcv() -> OHLCVData:
    n = 60
    np.random.seed(1)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df_daily = pd.DataFrame({
        "Open": close * 0.999, "High": close * 1.005,
        "Low": close * 0.995, "Close": close,
        "Volume": np.random.randint(1_000_000, 5_000_000, n).astype(float),
    })
    df_weekly = df_daily.copy()
    return OHLCVData("AAPL", df_daily, df_weekly, float(close[-1]), 1.5)

def test_build_signal_result():
    data = _mock_ohlcv()
    result = build_signal_result(
        ticker="AAPL", name="苹果", sector="信息技术·消费电子",
        market="stock", ohlcv=data
    )
    assert result.ticker == "AAPL"
    assert result.short_term.score in range(-4, 5)
    assert result.long_term.score in range(-4, 5)
    assert result.price > 0

def test_scan_single_returns_none_on_bad_ticker():
    with patch("services.scanner_service.fetch_ohlcv", return_value=None):
        result = scan_single("INVALID", "无效", "无", "stock")
    assert result is None
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_scanner_service.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 services/scanner_service.py**

```python
import asyncio
import json
from datetime import datetime
from models import SignalResult
from services.data_fetcher import fetch_ohlcv, OHLCVData
from services.indicator_engine import calculate_indicators, IndicatorValues
from services.signal_engine import compute_short_term, compute_long_term
from data.universe import get_all_tickers, is_forex

def build_signal_result(
    ticker: str, name: str, sector: str, market: str, ohlcv: OHLCVData
) -> SignalResult:
    daily_vals = calculate_indicators(ohlcv.daily)
    weekly_vals = calculate_indicators(ohlcv.weekly, is_weekly=True)

    # Merge weekly RSI into daily vals for long-term signal
    daily_vals.rsi_weekly = weekly_vals.rsi_weekly

    short_term = compute_short_term(daily_vals)
    long_term = compute_long_term(daily_vals)

    return SignalResult(
        ticker=ticker, name=name, sector=sector, market=market,
        price=ohlcv.current_price, change_pct=ohlcv.change_pct,
        short_term=short_term, long_term=long_term,
        scanned_at=datetime.utcnow(),
    )

def scan_single(ticker: str, name: str, sector: str, market: str) -> SignalResult | None:
    ohlcv = fetch_ohlcv(ticker)
    if ohlcv is None:
        return None
    return build_signal_result(ticker, name, sector, market, ohlcv)

async def run_full_scan(db) -> int:
    """Scan all universe assets, persist results to DB. Returns count of successful scans."""
    from services.notifier import check_price_alerts, check_signal_alerts
    from services.indicator_engine import calculate_indicators

    tickers = get_all_tickers()
    count = 0
    for item in tickers:
        ticker = item["ticker"]
        market = "forex" if is_forex(ticker) else "stock"
        result = scan_single(ticker, item["name"], item["sector"], market)
        if result is None:
            continue
        await db.execute("""
            INSERT OR REPLACE INTO scan_results
            (ticker, name, sector, market, price, change_pct,
             short_score, short_label, short_color,
             long_score, long_label, long_color,
             short_indicators, long_indicators, scanned_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            result.ticker, result.name, result.sector, result.market,
            result.price, result.change_pct,
            result.short_term.score, result.short_term.label, result.short_term.color,
            result.long_term.score, result.long_term.label, result.long_term.color,
            json.dumps([i.model_dump() for i in result.short_term.indicators]),
            json.dumps([i.model_dump() for i in result.long_term.indicators]),
            result.scanned_at.isoformat(),
        ))
        # 检查价格提醒和信号提醒（仅自选股触发通知）
        rsi_raw = next(
            (float(ind.raw_value) for ind in result.short_term.indicators if ind.name == "RSI(14)"),
            50.0,
        )
        await check_price_alerts(ticker, result.price)
        await check_signal_alerts(ticker, result.short_term.score, result.long_term.score, rsi_raw)
        count += 1
    await db.commit()
    return count
```

- [ ] **Step 4: 写 services/scheduler.py**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import get_db
from services.scanner_service import run_full_scan

scheduler = AsyncIOScheduler()

async def _scheduled_scan():
    async with get_db() as db:
        count = await run_full_scan(db)
    print(f"[Scheduler] Scan complete: {count} assets processed")

def start_scheduler():
    # 美股：美东时间 16:05（UTC 21:05，夏令时 20:05）
    scheduler.add_job(_scheduled_scan, CronTrigger(hour=21, minute=5), id="stock_scan")
    # 外汇：每4小时
    scheduler.add_job(_scheduled_scan, CronTrigger(hour="0,4,8,12,16,20"), id="fx_scan")
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
```

- [ ] **Step 5: 更新 main.py 加入调度器**

```python
from services.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()
```

- [ ] **Step 6: 运行测试，确认通过**

```bash
pytest tests/test_scanner_service.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add stock-tool/backend/services/scanner_service.py stock-tool/backend/services/scheduler.py stock-tool/backend/main.py
git commit -m "feat: scanner service and APScheduler cron tasks"
```

---

## Task 9: Watchlist、Scanner 和 Analysis API

**Files:**
- Modify: `stock-tool/backend/routers/watchlist.py`
- Modify: `stock-tool/backend/routers/scanner.py`
- Modify: `stock-tool/backend/routers/analysis.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_routers.py
import pytest
import json
from httpx import AsyncClient, ASGITransport
from main import app

async def _get_token(client):
    r = await client.post("/auth/login", json={"password": "changeme"})
    return r.json()["access_token"]

@pytest.mark.asyncio
async def test_watchlist_add_and_get():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.post("/watchlist", json={
            "ticker": "AAPL", "name": "苹果",
            "market": "stock", "sector": "信息技术·消费电子"
        }, headers=headers)
        assert r.status_code == 200
        r2 = await client.get("/watchlist", headers=headers)
        tickers = [item["ticker"] for item in r2.json()]
        assert "AAPL" in tickers

@pytest.mark.asyncio
async def test_watchlist_delete():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/watchlist", json={
            "ticker": "TSLA", "name": "特斯拉", "market": "stock", "sector": "电动车"
        }, headers=headers)
        r = await client.delete("/watchlist/TSLA", headers=headers)
        assert r.status_code == 200

@pytest.mark.asyncio
async def test_scanner_results_empty_initially():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/scanner/results", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_routers.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 routers/watchlist.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from routers.auth import require_auth
from database import get_db
from models import WatchlistItem

router = APIRouter()

@router.get("")
async def get_watchlist(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

@router.post("")
async def add_to_watchlist(item: WatchlistItem, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, name, market, sector) VALUES (?,?,?,?)",
            (item.ticker, item.name, item.market, item.sector)
        )
        await db.commit()
    return {"status": "ok"}

@router.delete("/{ticker}")
async def remove_from_watchlist(ticker: str, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("DELETE FROM watchlist WHERE ticker=?", (ticker,))
        await db.commit()
    return {"status": "ok"}
```

- [ ] **Step 4: 写 routers/scanner.py**

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from routers.auth import require_auth
from database import get_db
from services.scanner_service import run_full_scan
import json

router = APIRouter()

@router.get("/results")
async def get_scan_results(
    market: str = "all",
    signal_type: str = "all",
    sort_by: str = "short",
    _=Depends(require_auth)
):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM scan_results")
        rows = await cursor.fetchall()

    results = [dict(r) for r in rows]

    for r in results:
        r["short_indicators"] = json.loads(r.get("short_indicators") or "[]")
        r["long_indicators"] = json.loads(r.get("long_indicators") or "[]")

    if market != "all":
        results = [r for r in results if r["market"] == market]

    if signal_type == "bullish":
        results = [r for r in results if r["short_score"] > 0 or r["long_score"] > 0]
    elif signal_type == "bearish":
        results = [r for r in results if r["short_score"] < 0 or r["long_score"] < 0]

    key = "short_score" if sort_by == "short" else "long_score"
    results.sort(key=lambda x: abs(x.get(key, 0)), reverse=True)

    return results

@router.post("/trigger")
async def trigger_scan(background_tasks: BackgroundTasks, _=Depends(require_auth)):
    async def _run():
        async with get_db() as db:
            await run_full_scan(db)
    background_tasks.add_task(_run)
    return {"status": "scan started"}

@router.get("/last-scan-time")
async def last_scan_time(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute("SELECT MAX(scanned_at) as last_scan FROM scan_results")
        row = await cursor.fetchone()
    return {"last_scan": row["last_scan"] if row else None}
```

- [ ] **Step 5: 写 routers/analysis.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from routers.auth import require_auth
from services.data_fetcher import fetch_ohlcv
from services.scanner_service import build_signal_result
from data.universe import get_ticker_info, is_forex
from config import settings
import anthropic

router = APIRouter()

@router.get("/{ticker}")
async def get_analysis(ticker: str, _=Depends(require_auth)):
    info = get_ticker_info(ticker)
    if info is None:
        raise HTTPException(status_code=404, detail="Ticker not found in universe")
    ohlcv = fetch_ohlcv(ticker)
    if ohlcv is None:
        raise HTTPException(status_code=503, detail="Failed to fetch market data")
    market = "forex" if is_forex(ticker) else "stock"
    result = build_signal_result(ticker, info["name"], info["sector"], market, ohlcv)

    prices = ohlcv.daily["Close"].tail(30).tolist()
    return {
        "signal": result.model_dump(),
        "price_history": prices,
    }

@router.post("/{ticker}/deep")
async def deep_analysis(ticker: str, _=Depends(require_auth)):
    if not settings.claude_api_key:
        raise HTTPException(status_code=501, detail="Claude API key not configured")
    info = get_ticker_info(ticker)
    if info is None:
        raise HTTPException(status_code=404, detail="Ticker not found")
    ohlcv = fetch_ohlcv(ticker)
    if ohlcv is None:
        raise HTTPException(status_code=503, detail="Failed to fetch market data")
    market = "forex" if is_forex(ticker) else "stock"
    result = build_signal_result(ticker, info["name"], info["sector"], market, ohlcv)

    short = result.short_term
    long_ = result.long_term
    prompt = f"""
你是一位专业的技术分析师，请用中文对以下品种给出约200字的分析摘要，语言简洁易懂，面向没有专业背景的个人投资者。

品种：{info['name']}（{ticker}），板块：{info['sector']}
当前价格：{result.price}，涨跌：{result.change_pct:+.2f}%

短期信号（{short.label}，{short.score}/4分）：
{chr(10).join([f"- {i.name}：{i.description}" for i in short.indicators])}

长期信号（{long_.label}，{long_.score}/4分）：
{chr(10).join([f"- {i.name}：{i.description}" for i in long_.indicators])}

请综合以上信息给出分析摘要，包含当前趋势判断和需要注意的风险。
    """
    client = anthropic.Anthropic(api_key=settings.claude_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"analysis": message.content[0].text}
```

- [ ] **Step 6: 运行测试，确认通过**

```bash
pytest tests/test_routers.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add stock-tool/backend/routers/
git commit -m "feat: watchlist, scanner, and analysis API endpoints"
```

---

## Task 10: 提醒 API + 信号变化检测

**Files:**
- Modify: `stock-tool/backend/routers/alerts.py`
- Create: `stock-tool/backend/services/notifier.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_alerts.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

async def _get_token(client):
    r = await client.post("/auth/login", json={"password": "changeme"})
    return r.json()["access_token"]

@pytest.mark.asyncio
async def test_create_price_alert():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.post("/alerts/price", json={
            "ticker": "AAPL", "condition": "above", "threshold": 200.0
        }, headers=headers)
        assert r.status_code == 200
        assert "id" in r.json()

@pytest.mark.asyncio
async def test_create_signal_alert():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.post("/alerts/signal", json={
            "ticker": "NVDA", "condition": "any_change"
        }, headers=headers)
        assert r.status_code == 200

@pytest.mark.asyncio
async def test_get_alert_history():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/alerts/history", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
```

- [ ] **Step 2: 运行，确认失败**

```bash
pytest tests/test_alerts.py -v
```

Expected: FAIL

- [ ] **Step 3: 写 routers/alerts.py**

```python
from fastapi import APIRouter, Depends
from routers.auth import require_auth
from database import get_db
from models import PriceAlertCreate, SignalAlertCreate

router = APIRouter()

@router.post("/price")
async def create_price_alert(alert: PriceAlertCreate, _=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO price_alerts (ticker, condition, threshold) VALUES (?,?,?)",
            (alert.ticker, alert.condition, alert.threshold)
        )
        await db.commit()
    return {"id": cursor.lastrowid}

@router.get("/price")
async def get_price_alerts(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM price_alerts ORDER BY created_at DESC")
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

@router.delete("/price/{alert_id}")
async def delete_price_alert(alert_id: int, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("DELETE FROM price_alerts WHERE id=?", (alert_id,))
        await db.commit()
    return {"status": "ok"}

@router.post("/signal")
async def create_signal_alert(alert: SignalAlertCreate, _=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO signal_alerts (ticker, condition) VALUES (?,?)",
            (alert.ticker, alert.condition)
        )
        await db.commit()
    return {"id": cursor.lastrowid}

@router.get("/signal")
async def get_signal_alerts(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM signal_alerts ORDER BY created_at DESC")
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

@router.delete("/signal/{alert_id}")
async def delete_signal_alert(alert_id: int, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("DELETE FROM signal_alerts WHERE id=?", (alert_id,))
        await db.commit()
    return {"status": "ok"}

@router.get("/history")
async def get_alert_history(limit: int = 30, _=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM alert_history ORDER BY triggered_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

@router.post("/history/{alert_id}/read")
async def mark_as_read(alert_id: int, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("UPDATE alert_history SET read=1 WHERE id=?", (alert_id,))
        await db.commit()
    return {"status": "ok"}

@router.get("/unread-count")
async def unread_count(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM alert_history WHERE read=0")
        row = await cursor.fetchone()
    return {"count": row["cnt"]}
```

- [ ] **Step 4: 写 services/notifier.py**

```python
import aiosmtplib
from email.mime.text import MIMEText
from config import settings
from database import get_db
from datetime import datetime

async def send_email(subject: str, body: str):
    if not settings.smtp_user or not settings.notify_email:
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = settings.notify_email
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            start_tls=True,
        )
    except Exception as e:
        print(f"[Notifier] Email failed: {e}")

async def record_and_notify(ticker: str, alert_type: str, message: str):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO alert_history (ticker, alert_type, message) VALUES (?,?,?)",
            (ticker, alert_type, message)
        )
        await db.commit()
    await send_email(f"[投资工具] {ticker} 提醒", message)

async def check_price_alerts(ticker: str, current_price: float):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM price_alerts WHERE ticker=? AND active=1", (ticker,)
        )
        alerts = await cursor.fetchall()
    for alert in alerts:
        triggered = (
            (alert["condition"] == "above" and current_price > alert["threshold"]) or
            (alert["condition"] == "below" and current_price < alert["threshold"])
        )
        if triggered:
            msg = f"{ticker} 当前价格 {current_price} 已{'突破' if alert['condition']=='above' else '跌破'} {alert['threshold']}"
            await record_and_notify(ticker, "price", msg)

async def check_signal_alerts(ticker: str, new_short_score: int, new_long_score: int, rsi_daily: float):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM previous_signals WHERE ticker=?", (ticker,))
        prev = await cursor.fetchone()
        cursor2 = await db.execute("SELECT * FROM signal_alerts WHERE ticker=? AND active=1", (ticker,))
        alerts = await cursor2.fetchall()

    for alert in alerts:
        cond = alert["condition"]
        triggered = False
        message = ""

        if cond == "any_change" and prev:
            if abs(new_short_score - prev["short_score"]) >= 2 or abs(new_long_score - prev["long_score"]) >= 2:
                triggered = True
                message = f"{ticker} 信号发生跳变：短期评分 {prev['short_score']} → {new_short_score}"
        elif cond == "strong_only":
            if abs(new_short_score) >= 3 or abs(new_long_score) >= 3:
                triggered = True
                message = f"{ticker} 出现强烈信号：短期{new_short_score}/4，长期{new_long_score}/4"
        elif cond == "rsi_extreme":
            if rsi_daily < 30 or rsi_daily > 70:
                triggered = True
                direction = "超卖" if rsi_daily < 30 else "超买"
                message = f"{ticker} RSI({rsi_daily:.1f})进入{direction}区间"

        if triggered:
            await record_and_notify(ticker, "signal", message)

    async with get_db() as db:
        await db.execute("""
            INSERT OR REPLACE INTO previous_signals (ticker, short_score, long_score, rsi_daily, updated_at)
            VALUES (?,?,?,?,?)
        """, (ticker, new_short_score, new_long_score, rsi_daily, datetime.utcnow().isoformat()))
        await db.commit()
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
pytest tests/test_alerts.py -v
```

Expected: PASS

- [ ] **Step 6: 运行全部测试**

```bash
pytest -v
```

Expected: 所有测试通过。

- [ ] **Step 7: Commit**

```bash
git add stock-tool/backend/routers/alerts.py stock-tool/backend/services/notifier.py
git commit -m "feat: alerts API and email notifier with signal change detection"
```

---

## Task 11: conftest 与测试环境配置

**Files:**
- Create: `stock-tool/backend/tests/conftest.py`

- [ ] **Step 1: 写 conftest.py（确保测试用独立 DB）**

```python
# tests/conftest.py
import pytest
import os

os.environ.setdefault("APP_PASSWORD", "changeme")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-64chars-padded-here")
os.environ.setdefault("DATABASE_URL", ":memory:")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_USER", "")
os.environ.setdefault("NOTIFY_EMAIL", "")

pytest_plugins = ("anyio",)
```

在 `backend/` 根目录创建 `pytest.ini`：

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 2: 运行完整测试套件**

```bash
pytest -v --tb=short
```

Expected: 所有测试通过（不包含需要网络的 `test_data_fetcher.py`，可用 `-k "not data_fetcher"` 跳过网络测试）

- [ ] **Step 3: Commit**

```bash
git add stock-tool/backend/tests/conftest.py stock-tool/backend/pytest.ini
git commit -m "test: configure pytest with async mode and isolated test DB"
```

---

后端实现完成。运行 `uvicorn main:app --reload` 后访问 http://localhost:8000/docs 可测试所有 API。
