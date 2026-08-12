import pandas as pd

from app.signal_engine import IndicatorVotes, compute_votes, decide_direction


def _df_from_closes(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
        }
    )


def test_decide_direction_needs_three_of_four_buy():
    votes = IndicatorVotes(rsi="buy", ema_cross="buy", macd="buy", donchian=None)
    assert decide_direction(votes) == "BUY"


def test_decide_direction_needs_three_of_four_sell():
    votes = IndicatorVotes(rsi="sell", ema_cross="sell", macd=None, donchian="sell")
    assert decide_direction(votes) == "SELL"


def test_decide_direction_two_of_four_is_none():
    votes = IndicatorVotes(rsi="buy", ema_cross="buy", macd=None, donchian=None)
    assert decide_direction(votes) is None


def test_decide_direction_mixed_votes_is_none():
    votes = IndicatorVotes(rsi="buy", ema_cross="sell", macd="buy", donchian="sell")
    assert decide_direction(votes) is None


def test_decide_direction_all_four_buy_is_buy():
    votes = IndicatorVotes(rsi="buy", ema_cross="buy", macd="buy", donchian="buy")
    assert decide_direction(votes) == "BUY"


def test_decide_direction_all_none_is_none():
    votes = IndicatorVotes(rsi=None, ema_cross=None, macd=None, donchian=None)
    assert decide_direction(votes) is None


def test_compute_votes_detects_oversold_rsi_as_buy():
    # Strictly decreasing closes push RSI toward 0 (oversold -> buy)
    closes = [100.0 - i for i in range(40)]
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.rsi == "buy"


def test_compute_votes_detects_overbought_rsi_as_sell():
    closes = [100.0 + i for i in range(40)]
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.rsi == "sell"


def test_compute_votes_ema_cross_event_is_buy():
    # 30 flat bars at 10 (both EMAs settle at 10), then one bar jumps to 20.
    # The fast EMA (9) crosses above the slow EMA (21) on exactly the last bar.
    closes = [10.0] * 30 + [20.0] * 1
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.ema_cross == "buy"


def test_compute_votes_ema_cross_sustained_condition_is_none():
    # Same jump as above, but 10 bars later: fast EMA has been above slow EMA
    # for a while already, so the crossover *event* is in the past, not on
    # the last bar. A vote based on sustained condition (rather than the
    # crossover event) would wrongly fire "buy" here.
    closes = [10.0] * 30 + [20.0] * 10
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.ema_cross is None


def test_compute_votes_macd_cross_event_is_buy():
    # Same construction as the EMA case: MACD line crosses above its signal
    # line on exactly the last bar.
    closes = [10.0] * 30 + [20.0] * 1
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.macd == "buy"


def test_compute_votes_macd_cross_sustained_condition_is_none():
    # 6 bars after the jump, MACD line has been above the signal line for
    # several bars already -- no fresh crossover on the last bar.
    closes = [10.0] * 30 + [20.0] * 6
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.macd is None


def test_compute_votes_donchian_breakout_buy():
    # 25 flat bars, then a large jump that breaks above the prior 20-period
    # Donchian upper band.
    closes = [10.0] * 25 + [50.0]
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.donchian == "buy"


def test_compute_votes_donchian_breakout_sell():
    closes = [10.0] * 25 + [-50.0]
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.donchian == "sell"


def test_compute_votes_donchian_no_breakout_is_none():
    closes = [10.0] * 26
    df = _df_from_closes(closes)
    votes = compute_votes(df)
    assert votes.donchian is None
