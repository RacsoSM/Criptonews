import pandas as pd

from app.indicators import rsi, ema, macd, donchian, atr, volume_ratio, pct_below_high


def test_rsi_all_gains_is_100():
    closes = pd.Series([float(i) for i in range(1, 20)])  # strictly increasing
    result = rsi(closes, period=14)
    assert result.iloc[-1] > 95


def test_rsi_all_losses_is_0():
    closes = pd.Series([float(i) for i in range(20, 1, -1)])  # strictly decreasing
    result = rsi(closes, period=14)
    assert result.iloc[-1] < 5


def test_rsi_flat_series_is_neutral():
    closes = pd.Series([100.0] * 30)  # no movement at all
    result = rsi(closes, period=14)
    assert abs(result.iloc[-1] - 50) < 1e-6


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


def test_volume_ratio_is_one_for_constant_volume():
    volumes = pd.Series([100.0] * 25)
    result = volume_ratio(volumes, period=20)
    assert abs(result.iloc[-1] - 1.0) < 1e-9


def test_volume_ratio_above_one_for_a_spike():
    volumes = pd.Series([100.0] * 20 + [300.0])
    result = volume_ratio(volumes, period=20)
    assert result.iloc[-1] > 2.5  # 300 vs a ~100 rolling average


def test_volume_ratio_is_nan_before_the_window_fills():
    volumes = pd.Series([100.0] * 5)
    result = volume_ratio(volumes, period=20)
    assert pd.isna(result.iloc[-1])


def test_pct_below_high_at_the_peak_is_zero():
    highs = pd.Series([80.0] * 89 + [100.0])
    assert pct_below_high(highs, current_price=100.0, window=90) == 0.0


def test_pct_below_high_computes_the_drawdown_from_the_windows_peak():
    highs = pd.Series([100.0] * 90)
    assert pct_below_high(highs, current_price=60.0, window=90) == 40.0


def test_pct_below_high_only_looks_within_the_window():
    # A much higher peak sits outside the 90-window; it must not count.
    highs = pd.Series([1000.0] + [100.0] * 90)
    assert pct_below_high(highs, current_price=80.0, window=90) == 20.0


def test_pct_below_high_returns_none_without_a_full_window():
    highs = pd.Series([100.0] * 40)  # only 40 candles, asking for 90
    assert pct_below_high(highs, current_price=80.0, window=90) is None


def test_pct_below_high_never_goes_negative_above_the_recorded_peak():
    # Current price higher than any recorded high (e.g. a live price fetched
    # after the last daily candle closed) must clamp to 0%, not a negative
    # "below the high" figure.
    highs = pd.Series([100.0] * 90)
    assert pct_below_high(highs, current_price=120.0, window=90) == 0.0
