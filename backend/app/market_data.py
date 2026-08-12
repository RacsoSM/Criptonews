import httpx
import pandas as pd

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def get_top_symbols(limit: int = 30) -> list[dict]:
    coingecko_resp = httpx.get(
        COINGECKO_MARKETS_URL,
        params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": limit, "page": 1},
        timeout=10,
    )
    if coingecko_resp.status_code >= 400:
        raise RuntimeError(f"CoinGecko API error: {coingecko_resp.status_code}")
    ranked = coingecko_resp.json()

    exchange_resp = httpx.get(BINANCE_EXCHANGE_INFO_URL, timeout=10)
    if exchange_resp.status_code >= 400:
        raise RuntimeError(f"Binance exchangeInfo API error: {exchange_resp.status_code}")
    binance_symbols = {s["symbol"] for s in exchange_resp.json()["symbols"]}

    result = []
    for coin in ranked:
        candidate = f"{coin['symbol'].upper()}USDT"
        if candidate in binance_symbols:
            result.append({"symbol": candidate, "name": coin["name"], "rank": coin["market_cap_rank"]})
    return result


def get_klines(symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame | None:
    try:
        resp = httpx.get(
            BINANCE_KLINES_URL,
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10,
        )
    except httpx.HTTPError:
        return None

    if resp.status_code >= 400:
        return None

    raw = resp.json()
    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
    ])
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df
