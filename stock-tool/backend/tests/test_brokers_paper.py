"""Schema-level tests for the paper-trading accounts table (Task 1)."""
import pytest
from database import init_db, get_db
from config import settings


async def _fetch_default_account(db):
    async with db.execute(
        "SELECT * FROM accounts WHERE id = 'default'"
    ) as cursor:
        return await cursor.fetchone()


async def _count_accounts(db):
    async with db.execute("SELECT COUNT(*) FROM accounts") as cursor:
        row = await cursor.fetchone()
        return row[0]


@pytest.mark.asyncio
async def test_default_account_seeded_after_init_db():
    """After init_db(), accounts table has exactly one row with id='default'."""
    async with get_db() as db:
        count = await _count_accounts(db)
        assert count == 1

        row = await _fetch_default_account(db)
        assert row is not None
        assert row["id"] == "default"
        assert row["type"] == "paper"
        assert row["broker_adapter"] == "paper"
        assert row["display_name"] == "默认虚拟账户"
        assert row["initial_cash"] == settings.paper_initial_cash
        assert row["cash_balance"] == settings.paper_initial_cash
        assert row["created_at"] is not None


@pytest.mark.asyncio
async def test_default_account_cash_balance_equals_initial_cash():
    """cash_balance equals paper_initial_cash after init."""
    async with get_db() as db:
        row = await _fetch_default_account(db)
        assert row is not None
        assert row["cash_balance"] == settings.paper_initial_cash
        assert row["cash_balance"] == row["initial_cash"]


@pytest.mark.asyncio
async def test_init_db_twice_does_not_reset_cash_balance():
    """INSERT OR IGNORE: calling init_db() again must not overwrite a mutated cash_balance."""
    mutated_balance = settings.paper_initial_cash - 5000.0

    # Mutate cash_balance to a different value
    async with get_db() as db:
        await db.execute(
            "UPDATE accounts SET cash_balance = ? WHERE id = 'default'",
            (mutated_balance,),
        )
        await db.commit()

    # Call init_db() a second time
    await init_db()

    # The mutated value must be preserved
    async with get_db() as db:
        row = await _fetch_default_account(db)
        assert row is not None
        assert row["cash_balance"] == mutated_balance
