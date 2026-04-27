from data.universe import SP500_TICKERS, FX_PAIRS, get_all_tickers, get_ticker_info, is_forex


def test_sp500_has_expected_stocks():
    tickers = {item["ticker"] for item in SP500_TICKERS}
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "NVDA" in tickers
    assert len(SP500_TICKERS) >= 30  # subset, not full 500


def test_sp500_items_have_required_fields():
    for item in SP500_TICKERS:
        assert "ticker" in item
        assert "name" in item
        assert "sector" in item


def test_fx_pairs_coverage():
    tickers = {item["ticker"] for item in FX_PAIRS}
    assert "EURUSD=X" in tickers
    assert "USDJPY=X" in tickers
    assert len(FX_PAIRS) == 20


def test_fx_pairs_items_have_required_fields():
    for item in FX_PAIRS:
        assert item["ticker"].endswith("=X")
        assert "name" in item
        assert "sector" in item


def test_get_all_tickers():
    all_tickers = get_all_tickers()
    assert len(all_tickers) == len(SP500_TICKERS) + len(FX_PAIRS)


def test_get_ticker_info():
    info = get_ticker_info("AAPL")
    assert info is not None
    assert info["name"] == "苹果"
    assert get_ticker_info("UNKNOWN_XYZ_123") is None


def test_is_forex():
    assert is_forex("EURUSD=X") is True
    assert is_forex("AAPL") is False
