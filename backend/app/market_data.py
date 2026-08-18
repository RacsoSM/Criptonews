import json

import httpx
import pandas as pd

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
# api.binance.com returns HTTP 451 (geo-blocked) from US-based IPs, which is
# where GitHub Actions runners live — data-api.binance.vision mirrors the same
# public market-data endpoints without that restriction.
BINANCE_EXCHANGE_INFO_URL = "https://data-api.binance.vision/api/v3/exchangeInfo"
BINANCE_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"
BINANCE_TICKER_PRICE_URL = "https://data-api.binance.vision/api/v3/ticker/price"


def get_top_symbols(limit: int = 30) -> list[dict]:
    # Stablecoins and Binance-unlisted tokens routinely occupy top-market-cap
    # ranks but never produce a `<SYMBOL>USDT` pair, so fetching exactly
    # `limit` candidates would silently shrink the tracked list below `limit`.
    # Over-fetch and stop once `limit` tradable coins are found instead.
    coingecko_resp = httpx.get(
        COINGECKO_MARKETS_URL,
        params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": min(limit * 4, 250), "page": 1},
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
        if len(result) >= limit:
            break
        candidate = f"{coin['symbol'].upper()}USDT"
        if candidate in binance_symbols:
            result.append({
                "symbol": candidate,
                "name": coin["name"],
                "rank": coin["market_cap_rank"],
                "image_url": coin.get("image"),
            })
    return result


def get_current_prices(symbols: list[str]) -> dict[str, float]:
    """Latest traded price for each symbol, fetched in a single batched call.

    Returns an empty dict on any failure (bad symbol, network error, rate
    limit) rather than raising — a missing current price should never break
    the coins listing, it should just leave that field null for this request.
    """
    if not symbols:
        return {}

    try:
        resp = httpx.get(
            BINANCE_TICKER_PRICE_URL,
            # Binance's `symbols` param rejects whitespace (its own validation
            # regex is `^\[("...","...")\]$`), so this must be compact JSON —
            # json.dumps' default separators insert a space after each comma.
            params={"symbols": json.dumps(symbols, separators=(",", ":"))},
            timeout=10,
        )
        if resp.status_code >= 400:
            return {}
        return {entry["symbol"]: float(entry["price"]) for entry in resp.json()}
    except httpx.HTTPError:
        return {}


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
