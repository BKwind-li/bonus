"""NAV snapshot service.

Computes and persists a point-in-time NAV record for a paper trading account.
"""

from __future__ import annotations

from datetime import datetime

from database import get_db
from models import NavPoint


async def snapshot_nav(
    account_id: str,
    current_prices: dict[str, float],
    now: datetime,
) -> NavPoint:
    """Compute and persist today's NAV snapshot for *account_id*.

    Steps:
    1. Read accounts.cash_balance and all positions for account_id.
    2. market_value = Σ over positions of (qty × current_prices[ticker]).
       For positions whose ticker is NOT in current_prices, use the
       position's avg_cost as a fallback (cold price).
    3. total_value = cash + market_value.
    4. INSERT OR REPLACE INTO nav_history (account_id, date, cash, market_value,
       total_value) for date = now.date().isoformat() (YYYY-MM-DD).
    5. Return the resulting NavPoint.
    """
    date_str = now.date().isoformat()  # YYYY-MM-DD

    async with get_db() as db:
        # 1. Read cash balance
        async with db.execute(
            "SELECT cash_balance FROM accounts WHERE id = ?", (account_id,)
        ) as cursor:
            acc_row = await cursor.fetchone()

        if acc_row is None:
            raise ValueError(f"Account '{account_id}' not found")

        cash = float(acc_row["cash_balance"])

        # 2. Read positions
        async with db.execute(
            "SELECT ticker, qty, avg_cost FROM positions WHERE account_id = ?",
            (account_id,),
        ) as cursor:
            position_rows = await cursor.fetchall()

        # 3. Compute market value with avg_cost fallback
        market_value = 0.0
        for row in position_rows:
            ticker = row["ticker"]
            qty = float(row["qty"])
            if ticker in current_prices:
                price = current_prices[ticker]
            else:
                # Fallback: use avg_cost when live price is unavailable
                price = float(row["avg_cost"])
            market_value += qty * price

        total_value = cash + market_value

        # 4. Persist with INSERT OR REPLACE (composite PK: account_id + date)
        await db.execute("BEGIN")
        try:
            await db.execute(
                """
                INSERT OR REPLACE INTO nav_history
                  (account_id, date, cash, market_value, total_value)
                VALUES (?, ?, ?, ?, ?)
                """,
                (account_id, date_str, cash, market_value, total_value),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    # 5. Return NavPoint
    return NavPoint(
        date=date_str,
        cash=cash,
        market_value=market_value,
        total_value=total_value,
    )
