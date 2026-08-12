import pandas as pd
import pytest

from app.indicators import atr
from app.models import Position, Signal
from app.positions_service import process_coin
from app.signal_engine import compute_votes


def _uptrend_df(n=60):
    closes = [100.0 + i for i in range(n)]
    return pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
    })


def _downtrend_df(n=60):
    closes = [200.0 - i for i in range(n)]
    return pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
    })


def test_buy_signal_opens_position_when_none_open(db_session, mocker):
    mocker.patch(
        "app.positions_service.decide_direction",
        return_value="BUY",
    )
    df = _uptrend_df()

    signal = process_coin(db_session, "BTCUSDT", df)

    assert signal is not None
    assert signal.signal_type == "BUY"
    position = db_session.query(Position).filter_by(coin_symbol="BTCUSDT").one()
    assert position.status == "OPEN"
    assert position.stop_loss < position.entry_price < position.take_profit


def test_buy_signal_ignored_when_position_already_open(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    df = _uptrend_df()

    process_coin(db_session, "BTCUSDT", df)
    second_signal = process_coin(db_session, "BTCUSDT", df)

    assert second_signal is None
    assert db_session.query(Position).filter_by(coin_symbol="BTCUSDT").count() == 1


def test_sell_signal_closes_open_position(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    process_coin(db_session, "BTCUSDT", _uptrend_df())

    mocker.patch("app.positions_service.decide_direction", return_value="SELL")
    sell_signal = process_coin(db_session, "BTCUSDT", _downtrend_df())

    assert sell_signal is not None
    assert sell_signal.signal_type == "SELL"
    position = db_session.query(Position).filter_by(coin_symbol="BTCUSDT").one()
    assert position.status == "CLOSED"
    assert position.closed_price is not None


def test_sell_signal_ignored_when_no_open_position(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="SELL")

    signal = process_coin(db_session, "BTCUSDT", _downtrend_df())

    assert signal is None


# --- additional coverage beyond the brief's four core cases ---


def test_no_direction_writes_nothing(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value=None)

    signal = process_coin(db_session, "BTCUSDT", _uptrend_df())

    assert signal is None
    assert db_session.query(Position).count() == 0
    assert db_session.query(Signal).count() == 0


def test_suppressed_buy_writes_no_signal_row(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    df = _uptrend_df()

    process_coin(db_session, "BTCUSDT", df)
    process_coin(db_session, "BTCUSDT", df)

    assert db_session.query(Signal).filter_by(coin_symbol="BTCUSDT").count() == 1


def test_suppressed_sell_writes_no_signal_row(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="SELL")

    process_coin(db_session, "BTCUSDT", _downtrend_df())

    assert db_session.query(Signal).count() == 0


def test_sl_and_tp_use_atr_multiples_at_entry(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    df = _uptrend_df()
    expected_atr = float(atr(df["high"], df["low"], df["close"]).iloc[-1])
    entry = float(df["close"].iloc[-1])

    process_coin(db_session, "BTCUSDT", df)

    position = db_session.query(Position).one()
    assert position.entry_price == pytest.approx(entry)
    assert position.stop_loss == pytest.approx(entry - 1.5 * expected_atr)
    assert position.take_profit == pytest.approx(entry + 3 * expected_atr)


def test_signal_records_votes_and_links_position(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    df = _uptrend_df()

    signal = process_coin(db_session, "BTCUSDT", df)

    position = db_session.query(Position).one()
    assert signal.position_id == position.id
    assert signal.price == pytest.approx(float(df["close"].iloc[-1]))
    # votes are persisted verbatim from the real compute_votes on this frame
    expected = compute_votes(df)
    assert signal.rsi_vote == expected.rsi
    assert signal.ema_cross_vote == expected.ema_cross
    assert signal.macd_vote == expected.macd
    assert signal.donchian_vote == expected.donchian
    # sanity: this frame produces at least one real (non-None) vote, so the
    # equality checks above are not all trivially None == None
    assert signal.rsi_vote == "sell"


def test_sell_closes_only_the_matching_coins_position(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    process_coin(db_session, "BTCUSDT", _uptrend_df())
    process_coin(db_session, "ETHUSDT", _uptrend_df())

    mocker.patch("app.positions_service.decide_direction", return_value="SELL")
    process_coin(db_session, "BTCUSDT", _downtrend_df())

    btc = db_session.query(Position).filter_by(coin_symbol="BTCUSDT").one()
    eth = db_session.query(Position).filter_by(coin_symbol="ETHUSDT").one()
    assert btc.status == "CLOSED"
    assert eth.status == "OPEN"
    assert eth.closed_price is None


def test_buy_allowed_again_after_position_closed(db_session, mocker):
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    process_coin(db_session, "BTCUSDT", _uptrend_df())

    mocker.patch("app.positions_service.decide_direction", return_value="SELL")
    process_coin(db_session, "BTCUSDT", _downtrend_df())

    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    reopen = process_coin(db_session, "BTCUSDT", _uptrend_df())

    assert reopen is not None
    assert db_session.query(Position).filter_by(coin_symbol="BTCUSDT").count() == 2
    assert db_session.query(Position).filter_by(coin_symbol="BTCUSDT", status="OPEN").count() == 1


def test_process_coin_does_not_commit(db_session, mocker):
    """The transaction boundary belongs to the caller (get_session), not here."""
    mocker.patch("app.positions_service.decide_direction", return_value="BUY")
    commit = mocker.patch.object(db_session, "commit", wraps=db_session.commit)

    process_coin(db_session, "BTCUSDT", _uptrend_df())

    commit.assert_not_called()
    # rows are visible in the session (flushed) but not committed
    assert db_session.query(Position).count() == 1
    db_session.rollback()
    assert db_session.query(Position).count() == 0
