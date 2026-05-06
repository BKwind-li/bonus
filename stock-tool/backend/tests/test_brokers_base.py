"""Smoke tests for brokers.base — import correctness and type hierarchy only.

No real broker implementation exists at this stage (Task 2), so all tests are
synchronous and do not exercise runtime async behaviour.
"""

from brokers.base import (
    BrokerAdapter,
    BrokerError,
    InsufficientFundsError,
    InsufficientPositionError,
    InvalidOrderError,
    MarketClosedError,
    OrderNotFoundError,
)


def test_module_imports():
    """All public names can be imported from brokers.base without error."""
    # If we got here, every symbol resolved successfully.
    assert BrokerAdapter is not None
    assert BrokerError is not None
    assert InsufficientFundsError is not None
    assert InsufficientPositionError is not None
    assert InvalidOrderError is not None
    assert OrderNotFoundError is not None
    assert MarketClosedError is not None


def test_exception_hierarchy():
    """Each specific exception is a subclass of BrokerError -> Exception."""
    specific_exceptions = [
        InsufficientFundsError,
        InsufficientPositionError,
        InvalidOrderError,
        OrderNotFoundError,
        MarketClosedError,
    ]
    for exc_cls in specific_exceptions:
        assert issubclass(exc_cls, BrokerError), (
            f"{exc_cls.__name__} must inherit from BrokerError"
        )
        assert issubclass(exc_cls, Exception), (
            f"{exc_cls.__name__} must ultimately inherit from Exception"
        )
    # BrokerError itself is also an Exception
    assert issubclass(BrokerError, Exception)


def test_protocol_is_runtime_checkable():
    """BrokerAdapter must be decorated with @runtime_checkable.

    We verify this by confirming the class carries the ``_is_runtime_protocol``
    marker that typing injects and that isinstance() against a non-conforming
    object does not raise TypeError (it would raise if the Protocol were not
    runtime-checkable).
    """
    # Direct attribute check
    assert getattr(BrokerAdapter, "_is_runtime_protocol", False) is True, (
        "BrokerAdapter must be decorated with @runtime_checkable"
    )

    # isinstance() on a non-conforming plain object must return False,
    # not raise TypeError.
    class _NotAnAdapter:
        pass

    result = isinstance(_NotAnAdapter(), BrokerAdapter)
    assert result is False, (
        "A plain object that lacks all Protocol methods should not satisfy BrokerAdapter"
    )
