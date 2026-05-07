"""Portfolio router — paper-trading account management endpoints.

All endpoints require bearer-token authentication via require_auth.

Adapter access uses a Depends(get_adapter) pattern so tests can inject a fake
adapter via app.dependency_overrides[get_adapter] = lambda: fake_adapter.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Response

from brokers.base import (
    BrokerError,
    InsufficientFundsError,
    InsufficientPositionError,
    InvalidOrderError,
    MarketClosedError,
    OrderNotFoundError,
)
from brokers.paper import PaperBrokerAdapter
from database import get_db
from models import AccountInfo, Order, OrderRequest
from routers.auth import require_auth

router = APIRouter()

# ---------------------------------------------------------------------------
# Module-level default adapter (tests override via get_adapter dependency)
# ---------------------------------------------------------------------------

_adapter = PaperBrokerAdapter()  # default price_fetcher = data_fetcher.fetch_current_price


def get_adapter() -> PaperBrokerAdapter:
    """Return the module-level adapter instance.

    Override in tests:
        app.dependency_overrides[portfolio.get_adapter] = lambda: fake_adapter
    """
    return _adapter


# ---------------------------------------------------------------------------
# Price-fetcher dependency (tests can override for positions enrichment)
# ---------------------------------------------------------------------------

def _default_price_fetcher() -> Callable[[str], float | None]:
    from services.data_fetcher import fetch_current_price
    return fetch_current_price


def get_price_fetcher() -> Callable[[str], float | None]:
    """Return the current-price fetcher function.

    Override in tests:
        app.dependency_overrides[portfolio.get_price_fetcher] = lambda: lambda t: 150.0
    """
    return _default_price_fetcher()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _check_account_exists(account_id: str) -> None:
    """Raise 404 if account_id is not in the accounts table."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM accounts WHERE id = ?", (account_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="账户不存在")


async def _get_signal_snapshot(ticker: str) -> dict | None:
    """Query scan_results for the latest signal snapshot for *ticker*.

    Returns a dict with keys label_short, score_short, label_long, score_long,
    or None if no row exists.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT short_label, short_score, long_label, long_score "
            "FROM scan_results WHERE ticker = ?",
            (ticker,),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "label_short": row["short_label"],
        "score_short": row["short_score"],
        "label_long":  row["long_label"],
        "score_long":  row["long_score"],
    }


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@router.get("/accounts")
async def list_accounts(
    _=Depends(require_auth),
    adapter: PaperBrokerAdapter = Depends(get_adapter),
) -> list[AccountInfo]:
    """List all accounts (MVP: only default)."""
    account = await adapter.get_account("default")
    return [account]


@router.get("/accounts/{account_id}")
async def get_account(
    account_id: str,
    _=Depends(require_auth),
    adapter: PaperBrokerAdapter = Depends(get_adapter),
) -> AccountInfo:
    """Return a single account by id."""
    await _check_account_exists(account_id)
    return await adapter.get_account(account_id)


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

@router.get("/accounts/{account_id}/positions")
async def get_positions(
    account_id: str,
    _=Depends(require_auth),
    adapter: PaperBrokerAdapter = Depends(get_adapter),
    price_fetcher: Callable[[str], float | None] = Depends(get_price_fetcher),
):
    """Return positions enriched with current_price and unrealized P&L."""
    await _check_account_exists(account_id)
    positions = await adapter.get_positions(account_id)

    # Fetch prices in parallel via asyncio.to_thread (price_fetcher is synchronous)
    async def _fetch(ticker: str) -> float | None:
        return await asyncio.to_thread(price_fetcher, ticker)

    tickers = [p.ticker for p in positions]
    prices = await asyncio.gather(*[_fetch(t) for t in tickers])

    result = []
    for pos, price in zip(positions, prices):
        current_price = price if price is not None else pos.avg_cost
        market_value = pos.qty * current_price
        unrealized_pnl = (current_price - pos.avg_cost) * pos.qty
        unrealized_pnl_pct = (
            ((current_price - pos.avg_cost) / pos.avg_cost) * 100
            if pos.avg_cost != 0
            else 0.0
        )
        result.append({
            "ticker": pos.ticker,
            "qty": pos.qty,
            "avg_cost": pos.avg_cost,
            "opened_at": pos.opened_at,
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
        })
    return result


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@router.get("/accounts/{account_id}/orders")
async def get_orders(
    account_id: str,
    status: str | None = None,
    side: str | None = None,
    limit: int = 100,
    _=Depends(require_auth),
    adapter: PaperBrokerAdapter = Depends(get_adapter),
) -> list[Order]:
    """Return orders with optional status, side, and limit filters."""
    await _check_account_exists(account_id)
    orders = await adapter.get_orders(account_id, status=status)
    if side is not None:
        orders = [o for o in orders if o.side == side]
    return orders[:limit]


@router.post("/accounts/{account_id}/orders", status_code=201)
async def place_order(
    account_id: str,
    request: OrderRequest,
    _=Depends(require_auth),
    adapter: PaperBrokerAdapter = Depends(get_adapter),
) -> Order:
    """Place a new order; auto-injects signal snapshot from scan_results."""
    await _check_account_exists(account_id)

    snap = await _get_signal_snapshot(request.ticker)

    try:
        order = await adapter.place_order(account_id, request, signal_snapshot=snap)
        return order
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=f"现金不足: {e}")
    except InsufficientPositionError as e:
        raise HTTPException(status_code=400, detail=f"持仓不足: {e}")
    except InvalidOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MarketClosedError as e:
        raise HTTPException(status_code=400, detail=f"市场已关闭: {e}")
    except BrokerError as e:
        raise HTTPException(status_code=502, detail=f"broker error: {e}")


@router.delete("/accounts/{account_id}/orders/{order_id}")
async def cancel_order(
    account_id: str,
    order_id: str,
    _=Depends(require_auth),
    adapter: PaperBrokerAdapter = Depends(get_adapter),
) -> Order:
    """Cancel a queued or pending order."""
    await _check_account_exists(account_id)
    try:
        order = await adapter.cancel_order(account_id, order_id)
        return order
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="订单不存在")
    except InvalidOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# NAV history
# ---------------------------------------------------------------------------

@router.get("/accounts/{account_id}/nav-history")
async def get_nav_history(
    account_id: str,
    days: int = 90,
    _=Depends(require_auth),
):
    """Return NAV time series for the last *days* days."""
    await _check_account_exists(account_id)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT date, cash, market_value, total_value FROM nav_history "
            "WHERE account_id = ? AND date >= ? ORDER BY date ASC",
            (account_id, cutoff),
        )
        rows = await cursor.fetchall()
    return [
        {
            "date": r["date"],
            "cash": r["cash"],
            "market_value": r["market_value"],
            "total_value": r["total_value"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

@router.get("/accounts/{account_id}/performance")
async def get_performance(
    account_id: str,
    _=Depends(require_auth),
    adapter: PaperBrokerAdapter = Depends(get_adapter),
):
    """Return aggregate performance metrics.

    MVP returns: total_trades, total_buys, total_sells, total_return_pct.

    Deferred (too complex for MVP):
    - realized_pnl: requires per-fill cost-basis tracking on sells
    - unrealized_pnl: requires live price fetching
    - signal_win_rate: requires matching fill pairs (buy then subsequent sell)
    """
    await _check_account_exists(account_id)

    # Fetch account and positions for current portfolio value
    account = await adapter.get_account(account_id)
    positions = await adapter.get_positions(account_id)

    # Use latest nav_history total_value if available; else compute from cash + avg_cost
    async with get_db() as db:
        async with db.execute(
            "SELECT total_value FROM nav_history WHERE account_id = ? "
            "ORDER BY date DESC LIMIT 1",
            (account_id,),
        ) as cursor:
            nav_row = await cursor.fetchone()

    if nav_row is not None:
        current_total_value = nav_row["total_value"]
    else:
        position_value = sum(p.qty * p.avg_cost for p in positions)
        current_total_value = account.cash_balance + position_value

    initial_cash = account.initial_cash
    total_return_pct = (
        ((current_total_value - initial_cash) / initial_cash) * 100
        if initial_cash != 0
        else 0.0
    )

    # Count filled orders
    all_orders = await adapter.get_orders(account_id, status="filled")
    total_trades = len(all_orders)
    total_buys = sum(1 for o in all_orders if o.side == "buy")
    total_sells = sum(1 for o in all_orders if o.side == "sell")

    return {
        "total_trades": total_trades,
        "total_buys": total_buys,
        "total_sells": total_sells,
        "total_return_pct": round(total_return_pct, 4),
        # Deferred metrics — to be implemented in a later task
        "realized_pnl": 0,
        "unrealized_pnl": None,
        "signal_win_rate": None,
    }
