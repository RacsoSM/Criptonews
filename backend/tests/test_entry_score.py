import pandas as pd

from app.entry_score import compute_entry_score


def _df(closes, highs=None, lows=None, volumes=None):
    highs = highs if highs is not None else [c + 1 for c in closes]
    lows = lows if lows is not None else [c - 1 for c in closes]
    volumes = volumes if volumes is not None else [100.0] * len(closes)
    return pd.DataFrame({
        "open": closes, "high": highs, "low": lows, "close": closes, "volume": volumes,
    })


def test_returns_zero_for_too_few_candles():
    assert compute_entry_score(_df([100.0])) == 0.0


def test_score_is_always_within_bounds():
    closes = [100.0 + (i % 7) - 3 for i in range(60)]
    score = compute_entry_score(_df(closes))
    assert 0.0 <= score <= 100.0


def test_downtrend_scores_lower_than_the_same_dip_shape_in_an_uptrend():
    """The whole point of the trend-regime filter: an oversold dip is a much
    weaker buy case inside a strong downtrend than inside an uptrend pullback
    (buying the former looks more like catching a falling knife) — the score
    must reflect that, not just react to the dip's own RSI/MACD shape."""
    dip = [-i * 2.0 for i in range(1, 8)]

    uptrend = [100.0 + i * 1.5 for i in range(60)]
    closes_up = uptrend + [uptrend[-1] + d for d in dip]

    downtrend = [300.0 - i * 1.5 for i in range(60)]
    closes_down = downtrend + [downtrend[-1] + d for d in dip]

    score_up = compute_entry_score(_df(closes_up))
    score_down = compute_entry_score(_df(closes_down))

    assert score_up > score_down


def test_volume_spike_scores_higher_than_flat_volume_for_the_same_price_action():
    closes = [100.0 + i * 1.5 for i in range(60)] + [closes_end for closes_end in [
        100.0 + 59 * 1.5 - i * 2.0 for i in range(1, 6)
    ]]

    flat_volume = compute_entry_score(_df(closes, volumes=[100.0] * len(closes)))
    spiked = [100.0] * (len(closes) - 1) + [600.0]
    with_spike = compute_entry_score(_df(closes, volumes=spiked))

    assert with_spike > flat_volume


def test_relentless_uptrend_with_no_pullback_is_not_a_perfect_entry():
    """RSI stays overbought (never oversold) through a straight-line rally —
    the core indicators should not be maxed out just because price is above
    EMA50, since that alone isn't a real entry setup."""
    closes = [100.0 + i * 3 for i in range(60)]
    score = compute_entry_score(_df(closes))
    assert score < 60.0


def test_flat_market_scores_low():
    closes = [100.0] * 60
    score = compute_entry_score(_df(closes, volumes=[100.0] * 60))
    assert score < 40.0
