# backend/tests/test_routers_candles.py
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


def _fake_klines_df():
    closes = [100.0 + i for i in range(40)]
    return pd.DataFrame({
        "open_time": list(range(40)),
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
        "volume": [10.0] * 40,
    })


def test_get_candles_returns_series_with_indicators(mocker):
    mocker.patch("app.routers.candles.get_klines", return_value=_fake_klines_df())
    client = TestClient(app)

    response = client.get("/coins/BTCUSDT/candles")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 40
    assert body[-1]["ema_9"] is not None
    assert body[-1]["rsi_14"] is not None


def test_get_candles_returns_502_when_source_unavailable(mocker):
    mocker.patch("app.routers.candles.get_klines", return_value=None)
    client = TestClient(app)

    response = client.get("/coins/BTCUSDT/candles")

    assert response.status_code == 502


def test_get_candles_early_rows_have_null_indicators_not_nan(mocker):
    mocker.patch("app.routers.candles.get_klines", return_value=_fake_klines_df())
    client = TestClient(app)

    response = client.get("/coins/BTCUSDT/candles")

    assert response.status_code == 200
    body = response.json()
    first = body[0]
    # Before enough history exists (rsi period=14, donchian period=20),
    # these should be null, not NaN (which would make the JSON body
    # invalid / fail to parse).
    assert first["rsi_14"] is None
    assert first["donchian_upper"] is None
    assert first["donchian_lower"] is None
    # ema_9/ema_21/macd_line have no min_periods warm-up in this codebase's
    # ewm-based implementation, so they are always defined.
    assert first["ema_9"] is not None
    assert first["ema_21"] is not None
