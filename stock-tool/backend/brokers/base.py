"""BrokerAdapter Protocol and broker exception hierarchy.

All business-logic layers (routers, services) should depend only on the
types defined here.  Concrete adapters (PaperBrokerAdapter, future Alpaca
adapter, etc.) must satisfy the BrokerAdapter Protocol.
"""

from typing import Protocol, runtime_checkable

from models import AccountInfo, Order, OrderRequest, Position


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class BrokerError(Exception):
    """Base class for broker adapter errors."""


class InsufficientFundsError(BrokerError):
    """Account does not have enough cash to cover the buy order."""


class InsufficientPositionError(BrokerError):
    """Account does not hold enough shares/units to cover the sell order."""


class InvalidOrderError(BrokerError):
    """Order request failed validation (bad qty, missing limit_price, etc.)."""


class OrderNotFoundError(BrokerError):
    """Referenced order id does not exist for the given account."""


class MarketClosedError(BrokerError):
    """Market is closed and adapter is configured to reject (rather than queue)
    orders.  Paper adapter MVP queues instead, so this is reserved for future
    use."""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class BrokerAdapter(Protocol):
    """Pluggable broker interface.  PaperBrokerAdapter (Task 3) and any future
    real-account adapter (Alpaca/IB) implement this contract.

    All methods are async.  Implementations are responsible for transactional
    correctness over their own backing store.

    ``signal_snapshot`` passed to :meth:`place_order` is an optional dict with
    keys ``label_short``, ``score_short``, ``label_long``, ``score_long``.
    The router (Task 7) populates it from ``scan_results``; adapter
    implementations should treat it as opaque metadata and persist it verbatim
    onto the :class:`~models.Order` record.
    """

    name: str  # short identifier, e.g. "paper", "alpaca"

    async def get_account(self, account_id: str) -> AccountInfo: ...

    async def get_positions(self, account_id: str) -> list[Position]: ...

    async def get_orders(
        self, account_id: str, status: str | None = None
    ) -> list[Order]: ...

    async def place_order(
        self,
        account_id: str,
        request: OrderRequest,
        signal_snapshot: dict | None = None,
    ) -> Order: ...

    async def cancel_order(self, account_id: str, order_id: str) -> Order: ...
