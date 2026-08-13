# backend/app/entry_score.py
"""A 0-100 "how good a buy entry point is this coin right now" score.

This is deliberately NOT a second decision engine. It reuses the exact same
four indicators that drive real BUY signals (app.signal_engine) so the
number a user sees is a genuine preview of "how close is this to a real
signal" — never a parallel opinion that could contradict the actual push
notification.

What it adds on top of the 3-of-4 vote count:

1. Continuous strength instead of a binary vote. A RSI of 5 means much more
   than a RSI of 28, but signal_engine's vote treats both as an identical
   "buy". Each of the four indicators here contributes a 0-1 "how strongly
   does this indicator support buying" score instead of a yes/no flag.
2. Volume confirmation. A breakout or oversold bounce on below-average
   volume is a much weaker case than the same move on high volume — none of
   the four vote indicators look at volume at all.
3. A longer-term trend filter (EMA 50). The engine's most common failure
   mode is flagging "oversold" in the middle of a strong downtrend — buying
   there is closer to catching a falling knife than a real entry. This
   penalizes buying against the larger trend without ever touching the
   real signal logic in signal_engine.py.

Weights: 60% core (the four continuous indicator strengths, averaged), 20%
volume confirmation, 20% trend-regime alignment.
"""
import pandas as pd

from app.indicators import donchian, ema, macd, rsi, volume_ratio


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if pd.isna(value):
        return 0.0
    return max(lo, min(hi, float(value)))


def compute_entry_score(df: pd.DataFrame) -> float:
    """`df` has columns open, high, low, close, volume — same shape process_coin
    and compute_votes already expect. Returns a score in [0.0, 100.0].
    """
    if len(df) < 2:
        return 0.0

    closes = df["close"]
    highs = df["high"]
    lows = df["low"]
    volumes = df["volume"]

    # --- The same four indicators as signal_engine's vote, graded continuously ---
    rsi_value = rsi(closes).iloc[-1]
    rsi_strength = _clamp((30.0 - rsi_value) / 30.0)

    # 0.5% is calibrated against real 1h candles, not a round-number guess: a
    # fixed 2% (typical for daily charts) turned out to be far stricter than
    # actual hourly EMA9/21 spreads ever get for major pairs (p90 sits around
    # 0.3-0.7% across BTC/SOL/XRP/DOGE), which pinned this at ~0 even for
    # coins already showing a real bullish cross.
    ema_fast = ema(closes, 9).iloc[-1]
    ema_slow = ema(closes, 21).iloc[-1]
    ema_strength = (
        _clamp((ema_fast / ema_slow - 1.0) / 0.005) if ema_slow and ema_fast > ema_slow else 0.0
    )

    macd_line, signal_line = macd(closes)
    histogram = macd_line - signal_line
    macd_std = macd_line.rolling(26).std().iloc[-1]
    macd_strength = (
        _clamp(histogram.iloc[-1] / macd_std)
        if macd_std and macd_std > 0 and histogram.iloc[-1] > 0
        else 0.0
    )

    upper, lower = donchian(highs, lows, period=20)
    prior_upper = upper.iloc[-2]
    prior_lower = lower.iloc[-2]
    band_width = prior_upper - prior_lower if pd.notna(prior_upper) and pd.notna(prior_lower) else 0
    donchian_strength = (
        _clamp((closes.iloc[-1] - prior_upper) / band_width)
        if band_width and band_width > 0 and closes.iloc[-1] > prior_upper
        else 0.0
    )

    core = (rsi_strength + ema_strength + macd_strength + donchian_strength) / 4.0

    # --- Volume confirmation: is this move backed by real participation? ---
    vol_ratio = volume_ratio(volumes).iloc[-1]
    volume_strength = _clamp(vol_ratio - 1.0)

    # --- Trend regime: penalize buying against the longer-term trend. 0.5 at
    # price == EMA50, smoothly reaching 1.0 a full 1% above it and 0.0 a full
    # 1% below — a soft transition instead of a hard flip right at the line. ---
    ema50 = ema(closes, 50).iloc[-1]
    regime_strength = _clamp(0.5 + (closes.iloc[-1] / ema50 - 1.0) / 0.02) if ema50 else 0.0

    score = 0.6 * core + 0.2 * volume_strength + 0.2 * regime_strength
    return round(score * 100.0, 1)
