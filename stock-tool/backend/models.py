from pydantic import BaseModel, Field
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
