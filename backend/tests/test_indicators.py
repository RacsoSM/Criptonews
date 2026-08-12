import pandas as pd

from app.indicators import rsi, ema, macd, donchian, atr


def test_rsi_all_gains_is_100():
    closes = pd.Series([float(i) for i in range(1, 20)])  # strictly increasing
    result = rsi(closes, period=14)
    assert result.iloc[-1] > 95


def test_rsi_all_losses_is_0():
    closes = pd.Series([float(i) for i in range(20, 1, -1)])  # strictly decreasing
    result = rsi(closes, period=14)
    assert result.iloc[-1] < 5


def test_ema_reacts_faster_than_longer_period():
    closes = pd.Series([10.0] * 20 + [20.0] * 10)
    ema_fast = ema(closes, period=3)
    ema_slow = ema(closes, period=10)
    assert ema_fast.iloc[-1] > ema_slow.iloc[-1]


def test_macd_returns_two_series_same_length():
    closes = pd.Series([float(i) for i in range(1, 60)])
    macd_line, signal_line = macd(closes)
    assert len(macd_line) == len(closes)
    assert len(signal_line) == len(closes)


def test_donchian_upper_is_rolling_max_of_highs():
    highs = pd.Series([1.0, 5.0, 3.0, 2.0, 4.0])
    lows = pd.Series([0.5, 4.0, 2.5, 1.5, 3.5])
    upper, lower = donchian(highs, lows, period=3)
    assert upper.iloc[-1] == 4.0  # max of last 3 highs: [3,2,4]
    assert lower.iloc[-1] == 1.5  # min of last 3 lows: [2.5,1.5,3.5]


def test_atr_is_positive_for_volatile_series():
    highs = pd.Series([10.0, 12.0, 11.0, 13.0, 14.0] * 4)
    lows = pd.Series([8.0, 9.0, 8.5, 10.0, 11.0] * 4)
    closes = pd.Series([9.0, 11.0, 9.5, 12.0, 13.0] * 4)
    result = atr(highs, lows, closes, period=14)
    assert result.iloc[-1] > 0
