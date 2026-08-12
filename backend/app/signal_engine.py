from dataclasses import dataclass
from typing import Literal

import pandas as pd

from app.indicators import rsi, ema, macd, donchian

Vote = Literal["buy", "sell", None]


@dataclass
class IndicatorVotes:
    rsi: Vote
    ema_cross: Vote
    macd: Vote
    donchian: Vote


def _crossover_vote(fast: pd.Series, slow: pd.Series) -> Vote:
    """Detect a crossover *event* between two series on the last bar.

    Returns "buy" if `fast` crossed above `slow` on the last bar (was <=,
    now >), "sell" if it crossed below (was >=, now <), else None. Requires
    at least 2 rows to compare against; returns None otherwise instead of
    raising.
    """
    if len(fast) < 2 or len(slow) < 2:
        return None
    if fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
        return "buy"
    if fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
        return "sell"
    return None


def compute_votes(df: pd.DataFrame) -> IndicatorVotes:
    """Compute per-indicator buy/sell/None votes from an OHLC candle DataFrame.

    `df` must have `open, high, low, close` columns, ordered oldest to newest.
    Crossover-based votes (ema_cross, macd) only fire on the bar where the
    crossover *event* happens (comparing the last bar to the previous one),
    not for every bar where the sustained condition holds. On DataFrames
    with fewer than 2 rows, ema_cross/macd cannot compare a "previous" bar
    and simply vote None rather than raising.
    """
    closes = df["close"]
    highs = df["high"]
    lows = df["low"]

    rsi_series = rsi(closes)
    rsi_vote: Vote = None
    if rsi_series.iloc[-1] < 30:
        rsi_vote = "buy"
    elif rsi_series.iloc[-1] > 70:
        rsi_vote = "sell"

    ema_fast = ema(closes, 9)
    ema_slow = ema(closes, 21)
    ema_vote = _crossover_vote(ema_fast, ema_slow)

    macd_line, signal_line = macd(closes)
    macd_vote = _crossover_vote(macd_line, signal_line)

    upper, lower = donchian(highs, lows, period=20)
    donchian_vote: Vote = None
    if len(df) > 20:
        prior_upper = upper.iloc[-2]
        prior_lower = lower.iloc[-2]
        if closes.iloc[-1] > prior_upper:
            donchian_vote = "buy"
        elif closes.iloc[-1] < prior_lower:
            donchian_vote = "sell"

    return IndicatorVotes(rsi=rsi_vote, ema_cross=ema_vote, macd=macd_vote, donchian=donchian_vote)


def decide_direction(votes: IndicatorVotes) -> Literal["BUY", "SELL", None]:
    """Decide an overall direction from indicator votes using a 3-of-4 rule.

    Requires at least 3 of the 4 indicators to agree on the same direction;
    otherwise returns None (including when there's a majority of non-None
    votes but fewer than 3, or when votes are split between buy and sell).
    """
    vote_list = [votes.rsi, votes.ema_cross, votes.macd, votes.donchian]
    buy_count = vote_list.count("buy")
    sell_count = vote_list.count("sell")
    if buy_count >= 3:
        return "BUY"
    if sell_count >= 3:
        return "SELL"
    return None
