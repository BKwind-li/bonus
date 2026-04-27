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
