# backend/app/routers/candles.py
import pandas as pd
from fastapi import APIRouter, HTTPException

from app.indicators import rsi, ema, macd, donchian
from app.market_data import get_klines
from app.schemas import CandleOut

router = APIRouter(prefix="/coins", tags=["candles"])


def _none_if_nan(value: float) -> float | None:
    return None if pd.isna(value) else float(value)


@router.get("/{symbol}/candles", response_model=list[CandleOut])
def get_candles(symbol: str, limit: int = 100):
    df = get_klines(symbol, interval="1h", limit=limit)
    if df is None:
        raise HTTPException(status_code=502, detail="Market data unavailable")

    rsi_series = rsi(df["close"])
    ema_9 = ema(df["close"], 9)
    ema_21 = ema(df["close"], 21)
    macd_line, signal_line = macd(df["close"])
    upper, lower = donchian(df["high"], df["low"])

    result = []
    for i in range(len(df)):
        result.append(CandleOut(
            open_time=int(df["open_time"].iloc[i]),
            open=float(df["open"].iloc[i]),
            high=float(df["high"].iloc[i]),
            low=float(df["low"].iloc[i]),
            close=float(df["close"].iloc[i]),
            volume=float(df["volume"].iloc[i]),
            ema_9=_none_if_nan(ema_9.iloc[i]),
            ema_21=_none_if_nan(ema_21.iloc[i]),
            rsi_14=_none_if_nan(rsi_series.iloc[i]),
            macd_line=_none_if_nan(macd_line.iloc[i]),
            macd_signal=_none_if_nan(signal_line.iloc[i]),
            donchian_upper=_none_if_nan(upper.iloc[i]),
            donchian_lower=_none_if_nan(lower.iloc[i]),
        ))
    return result
