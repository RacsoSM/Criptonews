import httpx
import pytest

from app.market_data import get_top_symbols, get_klines


COINGECKO_SAMPLE = [
    {"symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1},
    {"symbol": "eth", "name": "Ethereum", "market_cap_rank": 2},
    {"symbol": "doesnotexistonbinance", "name": "Nowhere Coin", "market_cap_rank": 3},
]

BINANCE_EXCHANGE_INFO_SAMPLE = {
    "symbols": [
        {"symbol": "BTCUSDT"},
        {"symbol": "ETHUSDT"},
    ]
}

BINANCE_KLINES_SAMPLE = [
    [1700000000000, "60000.0", "60500.0", "59800.0", "60300.0", "123.45", 1700003600000, "0", 0, "0", "0", "0"],
    [1700003600000, "60300.0", "60700.0", "60100.0", "60600.0", "98.76", 1700007200000, "0", 0, "0", "0", "0"],
]


def test_get_top_symbols_filters_to_binance_pairs(mocker):
    def fake_get(url, params=None, timeout=None):
        if "coingecko" in url:
            return httpx.Response(200, json=COINGECKO_SAMPLE)
        if "exchangeInfo" in url:
            return httpx.Response(200, json=BINANCE_EXCHANGE_INFO_SAMPLE)
        raise AssertionError(f"unexpected URL {url}")

    mocker.patch("app.market_data.httpx.get", side_effect=fake_get)

    result = get_top_symbols(limit=3)

    assert result == [
        {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
        {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
    ]


def test_get_klines_returns_dataframe(mocker):
    mocker.patch(
        "app.market_data.httpx.get",
        return_value=httpx.Response(200, json=BINANCE_KLINES_SAMPLE),
    )

    df = get_klines("BTCUSDT", interval="1h", limit=2)

    assert list(df.columns) == ["open_time", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["close"].iloc[0] == 60300.0


def test_get_klines_returns_none_on_http_error(mocker):
    mocker.patch(
        "app.market_data.httpx.get",
        side_effect=httpx.HTTPError("boom"),
    )

    df = get_klines("BTCUSDT")

    assert df is None
