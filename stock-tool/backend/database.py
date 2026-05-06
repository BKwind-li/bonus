import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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
        """)
        await db.commit()
        await _seed_default_account(db)


async def _seed_default_account(db):
    """Insert the default paper account if it does not yet exist.

    Uses INSERT OR IGNORE keyed on the primary key id='default' so re-running
    init_db() never resets cash_balance or any other field. Consequence: the
    initial_cash and cash_balance values are FROZEN at first seed; changing
    PAPER_INITIAL_CASH in .env after the DB is created has no effect unless
    the database is reset (delete data.db).
    """
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT OR IGNORE INTO accounts
          (id, type, broker_adapter, display_name, initial_cash, cash_balance, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "default",
            "paper",
            "paper",
            "默认虚拟账户",
            settings.paper_initial_cash,
            settings.paper_initial_cash,
            now,
        ),
    )
    await db.commit()
