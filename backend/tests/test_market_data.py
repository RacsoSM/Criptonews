import httpx
import pytest

from app.market_data import get_top_symbols, get_klines, get_current_prices


COINGECKO_SAMPLE = [
    {
        "symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1,
        "image": "https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png",
    },
    {
        "symbol": "eth", "name": "Ethereum", "market_cap_rank": 2,
        "image": "https://coin-images.coingecko.com/coins/images/279/large/ethereum.png",
    },
    {"symbol": "doesnotexistonbinance", "name": "Nowhere Coin", "market_cap_rank": 3, "image": None},
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
        {
            "symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1,
            "image_url": "https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png",
        },
        {
            "symbol": "ETHUSDT", "name": "Ethereum", "rank": 2,
            "image_url": "https://coin-images.coingecko.com/coins/images/279/large/ethereum.png",
        },
    ]


def test_get_top_symbols_backfills_past_limit_to_reach_full_count(mocker):
    """Coins without a Binance pair (stablecoins, unlisted tokens) must not
    shrink the tracked list below `limit` — the next-ranked tradable coin
    should fill the gap instead of being left out.
    """
    coingecko_sample = [
        {"symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1, "image": None},
        {"symbol": "eth", "name": "Ethereum", "market_cap_rank": 2, "image": None},
        {"symbol": "usdt", "name": "Tether", "market_cap_rank": 3, "image": None},
        {"symbol": "sol", "name": "Solana", "market_cap_rank": 4, "image": None},
    ]
    binance_exchange_info = {
        "symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}, {"symbol": "SOLUSDT"}],
    }

    def fake_get(url, params=None, timeout=None):
        if "coingecko" in url:
            assert params["per_page"] > 3, "must ask CoinGecko for more than `limit` to allow backfill"
            return httpx.Response(200, json=coingecko_sample)
        if "exchangeInfo" in url:
            return httpx.Response(200, json=binance_exchange_info)
        raise AssertionError(f"unexpected URL {url}")

    mocker.patch("app.market_data.httpx.get", side_effect=fake_get)

    result = get_top_symbols(limit=3)

    assert [r["symbol"] for r in result] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


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


def test_get_klines_returns_none_on_non_2xx_status(mocker):
    mocker.patch(
        "app.market_data.httpx.get",
        return_value=httpx.Response(400, json={}),
    )

    df = get_klines("BTCUSDT")

    assert df is None


def test_get_top_symbols_raises_on_coingecko_error_status(mocker):
    def fake_get(url, params=None, timeout=None):
        if "coingecko" in url:
            return httpx.Response(400, json={"error": "bad request"})
        raise AssertionError(f"unexpected URL {url}")

    mocker.patch("app.market_data.httpx.get", side_effect=fake_get)

    with pytest.raises(RuntimeError):
        get_top_symbols(limit=3)


def test_get_top_symbols_raises_on_binance_exchange_info_error_status(mocker):
    def fake_get(url, params=None, timeout=None):
        if "coingecko" in url:
            return httpx.Response(200, json=COINGECKO_SAMPLE)
        if "exchangeInfo" in url:
            return httpx.Response(400, json={"error": "bad request"})
        raise AssertionError(f"unexpected URL {url}")

    mocker.patch("app.market_data.httpx.get", side_effect=fake_get)

    with pytest.raises(RuntimeError):
        get_top_symbols(limit=3)


def test_get_current_prices_returns_symbol_to_price_map(mocker):
    get_mock = mocker.patch(
        "app.market_data.httpx.get",
        return_value=httpx.Response(
            200,
            json=[
                {"symbol": "BTCUSDT", "price": "61234.50"},
                {"symbol": "ETHUSDT", "price": "3456.78"},
            ],
        ),
    )

    result = get_current_prices(["BTCUSDT", "ETHUSDT"])

    assert result == {"BTCUSDT": 61234.50, "ETHUSDT": 3456.78}
    # Binance's `symbols` param rejects any whitespace in the JSON array —
    # regression check for the space json.dumps inserts after each comma.
    sent_symbols = get_mock.call_args.kwargs["params"]["symbols"]
    assert " " not in sent_symbols
    assert sent_symbols == '["BTCUSDT","ETHUSDT"]'


def test_get_current_prices_returns_empty_dict_for_empty_input():
    assert get_current_prices([]) == {}


def test_get_current_prices_returns_empty_dict_on_http_error(mocker):
    mocker.patch("app.market_data.httpx.get", side_effect=httpx.HTTPError("boom"))

    assert get_current_prices(["BTCUSDT"]) == {}


def test_get_current_prices_returns_empty_dict_on_non_2xx_status(mocker):
    mocker.patch("app.market_data.httpx.get", return_value=httpx.Response(400, json={}))

    assert get_current_prices(["BTCUSDT"]) == {}
