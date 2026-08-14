# backend/tests/test_scheduler_job.py
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
from sqlalchemy.exc import OperationalError

from app.models import Coin, DeviceToken, EntryScoreHistory, Position
from app.scheduler import run_cycle


def _session_ctx(session):
    @contextmanager
    def _ctx():
        yield session

    return _ctx()


def _committing_session_ctx(session, log: list[str]):
    """A session context that commits on exit, recording when it did.

    Mirrors the real `get_session`, whose closing `commit()` is the moment a
    cycle's signals actually become durable.
    """

    @contextmanager
    def _ctx():
        yield session
        session.commit()
        log.append("commit")

    return _ctx()


def _notified(notify_mock):
    """(token, coin_symbol, signal_type, price) per notification attempt."""
    return [
        (call.args[0], call.args[1].coin_symbol, call.args[1].signal_type, call.args[1].price)
        for call in notify_mock.call_args_list
    ]


def _fake_klines_df():
    closes = [100.0 + i for i in range(40)]
    return pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
        "volume": [10.0] * len(closes),
    })


def test_run_cycle_refreshes_coins_generates_signal_and_notifies(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    fake_signal = SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0)
    mocker.patch("app.scheduler.process_coin", return_value=fake_signal)
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()

    assert db_session.query(Coin).filter_by(symbol="BTCUSDT").count() == 1
    assert _notified(notify_mock) == [("device-1", "BTCUSDT", "BUY", 140.0)]


def test_run_cycle_skips_coin_when_klines_unavailable(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=None)
    process_coin_mock = mocker.patch("app.scheduler.process_coin")
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    run_cycle()

    process_coin_mock.assert_not_called()
    notify_mock.assert_not_called()


def test_run_cycle_does_not_notify_when_no_signal_generated(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch("app.scheduler.process_coin", return_value=None)
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()

    notify_mock.assert_not_called()


def test_run_cycle_aborts_when_top_symbols_lookup_fails(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        side_effect=RuntimeError("CoinGecko API error: 429"),
    )
    klines_mock = mocker.patch("app.scheduler.get_klines")
    process_coin_mock = mocker.patch("app.scheduler.process_coin")
    notify_mock = mocker.patch("app.scheduler.send_signal_notification")

    run_cycle()  # must not raise

    klines_mock.assert_not_called()
    process_coin_mock.assert_not_called()
    notify_mock.assert_not_called()


def test_run_cycle_updates_existing_and_deactivates_dropped_coins(mocker, db_session):
    db_session.add(Coin(symbol="BTCUSDT", name="Bitcoin", rank=3, active=False))
    db_session.add(Coin(symbol="DOGEUSDT", name="Dogecoin", rank=9, active=True))
    db_session.commit()

    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[
            {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
            {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
        ],
    )
    mocker.patch("app.scheduler.get_klines", return_value=None)
    mocker.patch("app.scheduler.process_coin", return_value=None)
    mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    run_cycle()

    btc = db_session.query(Coin).filter_by(symbol="BTCUSDT").one()
    assert (btc.name, btc.rank, btc.active) == ("Bitcoin", 1, True)

    eth = db_session.query(Coin).filter_by(symbol="ETHUSDT").one()
    assert (eth.name, eth.rank, eth.active) == ("Ethereum", 2, True)

    doge = db_session.query(Coin).filter_by(symbol="DOGEUSDT").one()
    assert doge.active is False  # dropped from top-N, deactivated not deleted
    assert db_session.query(Coin).count() == 3


def test_run_cycle_notifies_every_token_for_every_signal(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[
            {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
            {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
        ],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    btc_signal = SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0)
    eth_signal = SimpleNamespace(coin_symbol="ETHUSDT", signal_type="SELL", price=90.0)
    mocker.patch("app.scheduler.process_coin", side_effect=[btc_signal, eth_signal])
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.add(DeviceToken(token="device-2"))
    db_session.commit()

    run_cycle()

    assert notify_mock.call_count == 4
    assert _notified(notify_mock) == [
        ("device-1", "BTCUSDT", "BUY", 140.0),
        ("device-2", "BTCUSDT", "BUY", 140.0),
        ("device-1", "ETHUSDT", "SELL", 90.0),
        ("device-2", "ETHUSDT", "SELL", 90.0),
    ]


def test_run_cycle_continues_when_process_coin_raises_for_one_coin(mocker, db_session):
    """One coin blowing up must not void the rest of the cycle's work."""
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[
            {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
            {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
        ],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    eth_signal = SimpleNamespace(coin_symbol="ETHUSDT", signal_type="BUY", price=140.0)
    mocker.patch(
        "app.scheduler.process_coin",
        side_effect=[RuntimeError("Multiple rows were found"), eth_signal],
    )
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()  # must not raise

    # The healthy coin still produced its signal and notification.
    assert _notified(notify_mock) == [("device-1", "ETHUSDT", "BUY", 140.0)]
    # And the cycle's coin-table refresh survived (session was not rolled back).
    assert db_session.query(Coin).filter_by(symbol="ETHUSDT").count() == 1


def test_run_cycle_aborts_remaining_coins_when_session_becomes_unusable(
    mocker, db_session, caplog
):
    """A flush-level failure poisons the transaction — stop instead of spamming.

    Per-coin isolation only holds while the session's transaction is still
    usable. Once a `session.flush()` inside `process_coin` fails, every
    remaining coin would raise `PendingRollbackError` rather than its own real
    error, so the cycle must log once and abort.
    """
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[
            {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
            {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
            {"symbol": "SOLUSDT", "name": "Solana", "rank": 3},
        ],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    process_coin_mock = mocker.patch(
        "app.scheduler.process_coin",
        side_effect=OperationalError(
            "INSERT INTO positions ...", {}, Exception("database is locked")
        ),
    )
    # What a failed flush leaves behind: a deactivated transaction.
    mocker.patch.object(type(db_session), "is_active", False)
    rollback_spy = mocker.spy(db_session, "rollback")
    notify_mock = mocker.patch("app.scheduler.send_signal_notification")

    with caplog.at_level(logging.ERROR, logger="app.scheduler"):
        run_cycle()  # must not raise

    # Stopped at the first coin: no grinding through the other two.
    process_coin_mock.assert_called_once()
    assert process_coin_mock.call_args[0][1] == "BTCUSDT"
    notify_mock.assert_not_called()

    # Rolled back once, so get_session's closing commit() cannot raise a
    # second, misleading PendingRollbackError.
    rollback_spy.assert_called_once_with()

    aborts = [
        r for r in caplog.records
        if "aborting the rest of this cycle" in r.getMessage()
    ]
    assert len(aborts) == 1
    assert aborts[0].levelno == logging.ERROR


def test_run_cycle_continues_when_notification_raises(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    fake_signal = SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0)
    mocker.patch("app.scheduler.process_coin", return_value=fake_signal)
    notify_mock = mocker.patch(
        "app.scheduler.send_signal_notification",
        side_effect=[OSError("boom"), True],
    )

    db_session.add(DeviceToken(token="device-1"))
    db_session.add(DeviceToken(token="device-2"))
    db_session.commit()

    run_cycle()  # must not raise

    assert notify_mock.call_count == 2  # second token still attempted
    assert db_session.query(Coin).filter_by(symbol="BTCUSDT").count() == 1


def test_run_cycle_still_monitors_coin_with_open_position_outside_top_n(
    mocker, db_session
):
    """A coin can only be exited by a SELL, which requires analysing it.

    If it drops out of the ranking while a position is open, dropping it from
    the cycle would strand that position open forever.
    """
    db_session.add(Coin(symbol="DOGEUSDT", name="Dogecoin", rank=31, active=True))
    db_session.add(Position(
        coin_symbol="DOGEUSDT",
        entry_price=0.1,
        entry_time=datetime.now(timezone.utc),
        stop_loss=0.09,
        take_profit=0.13,
        status="OPEN",
    ))
    db_session.commit()

    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    sell_signal = SimpleNamespace(coin_symbol="DOGEUSDT", signal_type="SELL", price=0.12)
    process_coin_mock = mocker.patch(
        "app.scheduler.process_coin", side_effect=[None, sell_signal]
    )
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()

    processed = [call.args[1] for call in process_coin_mock.call_args_list]
    assert processed == ["BTCUSDT", "DOGEUSDT"]
    # ...and the SELL that closes the stranded position still goes out.
    assert _notified(notify_mock) == [("device-1", "DOGEUSDT", "SELL", 0.12)]
    # The coin itself is still correctly deactivated in the ranking table.
    assert db_session.query(Coin).filter_by(symbol="DOGEUSDT").one().active is False


def test_run_cycle_does_not_duplicate_a_coin_in_both_top_n_and_open_positions(
    mocker, db_session
):
    db_session.add(Position(
        coin_symbol="BTCUSDT",
        entry_price=60000.0,
        entry_time=datetime.now(timezone.utc),
        stop_loss=57000.0,
        take_profit=66000.0,
        status="OPEN",
    ))
    db_session.commit()

    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    process_coin_mock = mocker.patch("app.scheduler.process_coin", return_value=None)
    mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    run_cycle()

    assert [call.args[1] for call in process_coin_mock.call_args_list] == ["BTCUSDT"]


def test_run_cycle_ignores_closed_positions_when_building_work_list(mocker, db_session):
    db_session.add(Position(
        coin_symbol="DOGEUSDT",
        entry_price=0.1,
        entry_time=datetime.now(timezone.utc),
        stop_loss=0.09,
        take_profit=0.13,
        status="CLOSED",
        closed_price=0.12,
        closed_time=datetime.now(timezone.utc),
    ))
    db_session.commit()

    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    process_coin_mock = mocker.patch("app.scheduler.process_coin", return_value=None)
    mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    run_cycle()

    assert [call.args[1] for call in process_coin_mock.call_args_list] == ["BTCUSDT"]


def test_run_cycle_notifies_only_after_the_transaction_commits(mocker, db_session):
    """A push is irreversible; the transaction is not.

    Sending inside the session risks advertising a signal that a later
    rollback erases from the DB.
    """
    order: list[str] = []
    mocker.patch(
        "app.scheduler.get_session",
        return_value=_committing_session_ctx(db_session, order),
    )
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch(
        "app.scheduler.process_coin",
        return_value=SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0),
    )

    def _record_send(token, signal):
        order.append("notify")
        return True

    mocker.patch("app.scheduler.send_signal_notification", side_effect=_record_send)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()

    assert order == ["commit", "notify"]


def test_run_cycle_sends_nothing_when_the_cycle_aborts_mid_loop(mocker, db_session):
    """The abort path rolls the cycle's signals back — nothing may be pushed."""
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[
            {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
            {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
        ],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    btc_signal = SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0)
    mocker.patch(
        "app.scheduler.process_coin",
        side_effect=[
            btc_signal,
            OperationalError("INSERT INTO positions ...", {}, Exception("db is locked")),
        ],
    )
    mocker.patch.object(type(db_session), "is_active", False)
    notify_mock = mocker.patch("app.scheduler.send_signal_notification")

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()  # must not raise

    # BTC's signal was generated, but the abort rolled it back, so the user
    # must not have been told about it.
    notify_mock.assert_not_called()


def test_run_cycle_passes_a_detached_snapshot_not_the_orm_row(mocker, db_session):
    """ORM rows are expired once the session commits/closes.

    Passing one to the notifier after the `with` block would raise
    DetachedInstanceError at attribute access time.
    """
    orm_like = SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0)
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch("app.scheduler.process_coin", return_value=orm_like)
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()

    pushed = notify_mock.call_args.args[1]
    assert pushed is not orm_like
    assert (pushed.coin_symbol, pushed.signal_type, pushed.price) == ("BTCUSDT", "BUY", 140.0)


def test_run_cycle_uses_configured_top_n_limit(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch("app.scheduler.settings.top_n_coins", 10)
    top_symbols_mock = mocker.patch("app.scheduler.get_top_symbols", return_value=[])
    mocker.patch("app.scheduler.get_klines", return_value=None)
    mocker.patch("app.scheduler.process_coin", return_value=None)

    run_cycle()

    top_symbols_mock.assert_called_once_with(limit=10)


def test_run_cycle_warns_when_fcm_send_reports_failure(mocker, db_session, caplog):
    """A silent False from FCM must not vanish: it means nothing was delivered."""
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch(
        "app.scheduler.process_coin",
        return_value=SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0),
    )
    mocker.patch("app.scheduler.send_signal_notification", return_value=False)

    db_session.add(DeviceToken(token="device-token-abc123"))
    db_session.commit()

    with caplog.at_level(logging.WARNING, logger="app.scheduler"):
        run_cycle()

    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "FCM send returned failure" in r.getMessage()
    ]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "abc123" in message  # which token
    assert "BUY" in message and "BTCUSDT" in message  # which signal


def test_run_cycle_logs_a_summary_line(mocker, db_session, caplog):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[
            {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
            {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
        ],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch(
        "app.scheduler.process_coin",
        side_effect=[
            SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0),
            None,
        ],
    )
    mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    with caplog.at_level(logging.INFO, logger="app.scheduler"):
        run_cycle()

    summaries = [r for r in caplog.records if "Cycle complete" in r.getMessage()]
    assert len(summaries) == 1
    assert summaries[0].levelno == logging.INFO
    assert summaries[0].getMessage() == (
        "Cycle complete: 2 coins processed, 1 signals generated, 1 notifications sent"
    )


def test_run_cycle_persists_entry_score_for_each_coin(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[
            {"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1},
            {"symbol": "ETHUSDT", "name": "Ethereum", "rank": 2},
        ],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch("app.scheduler.process_coin", return_value=None)
    mocker.patch(
        "app.scheduler.compute_entry_score",
        side_effect=[42.5, 7.0],
    )

    run_cycle()

    btc = db_session.query(Coin).filter_by(symbol="BTCUSDT").one()
    eth = db_session.query(Coin).filter_by(symbol="ETHUSDT").one()
    assert btc.entry_score == 42.5
    assert eth.entry_score == 7.0


def test_run_cycle_appends_an_entry_score_history_row_for_each_coin(mocker, db_session):
    # side_effect (not return_value): a @contextmanager instance is single-
    # use, and this test enters it twice via two separate run_cycle() calls.
    mocker.patch("app.scheduler.get_session", side_effect=lambda: _session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch("app.scheduler.process_coin", return_value=None)
    mocker.patch("app.scheduler.compute_entry_score", return_value=55.5)

    run_cycle()
    run_cycle()  # a second hourly cycle must APPEND, not overwrite

    history = (
        db_session.query(EntryScoreHistory).filter_by(coin_symbol="BTCUSDT").all()
    )
    assert len(history) == 2
    assert all(row.score == 55.5 for row in history)


def test_run_cycle_still_generates_signals_when_entry_score_computation_raises(
    mocker, db_session, caplog
):
    """Entry score is informational — a bug in it must never cost the cycle
    its real BUY/SELL signal or notification for that coin."""
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch("app.scheduler.get_klines", return_value=_fake_klines_df())
    mocker.patch("app.scheduler.compute_entry_score", side_effect=RuntimeError("boom"))
    fake_signal = SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0)
    mocker.patch("app.scheduler.process_coin", return_value=fake_signal)
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    with caplog.at_level(logging.ERROR, logger="app.scheduler"):
        run_cycle()  # must not raise

    assert _notified(notify_mock) == [("device-1", "BTCUSDT", "BUY", 140.0)]
    btc = db_session.query(Coin).filter_by(symbol="BTCUSDT").one()
    assert btc.entry_score is None  # computation failed, left untouched


def _fake_daily_df(peak=100.0, current=60.0, days=360):
    # Flat at `peak` except the very last candle, which closes at `current` —
    # gives a predictable, exact expected drawdown for every window size.
    highs = [peak] * (days - 1) + [current]
    closes = [peak] * (days - 1) + [current]
    return pd.DataFrame({
        "open": closes, "high": highs, "low": [c - 1 for c in closes],
        "close": closes, "volume": [10.0] * days,
    })


def _klines_by_interval(hourly_df, daily_df):
    def _side_effect(symbol, interval="1h", limit=100):
        return daily_df if interval == "1d" else hourly_df

    return _side_effect


def test_run_cycle_persists_drawdown_stats_for_each_coin(mocker, db_session):
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )
    mocker.patch(
        "app.scheduler.get_klines",
        side_effect=_klines_by_interval(_fake_klines_df(), _fake_daily_df(peak=100.0, current=60.0)),
    )
    mocker.patch("app.scheduler.process_coin", return_value=None)

    run_cycle()

    btc = db_session.query(Coin).filter_by(symbol="BTCUSDT").one()
    assert btc.pct_below_high_90d == 40.0
    assert btc.pct_below_high_180d == 40.0
    assert btc.pct_below_high_360d == 40.0


def test_run_cycle_still_generates_signals_when_drawdown_computation_raises(
    mocker, db_session
):
    """Same isolation as the entry score: a drawdown-stats bug must never
    cost the cycle its real BUY/SELL signal for that coin."""
    mocker.patch("app.scheduler.get_session", return_value=_session_ctx(db_session))
    mocker.patch(
        "app.scheduler.get_top_symbols",
        return_value=[{"symbol": "BTCUSDT", "name": "Bitcoin", "rank": 1}],
    )

    def _raise_on_daily(symbol, interval="1h", limit=100):
        if interval == "1d":
            raise RuntimeError("boom")
        return _fake_klines_df()

    mocker.patch("app.scheduler.get_klines", side_effect=_raise_on_daily)
    fake_signal = SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=140.0)
    mocker.patch("app.scheduler.process_coin", return_value=fake_signal)
    notify_mock = mocker.patch("app.scheduler.send_signal_notification", return_value=True)

    db_session.add(DeviceToken(token="device-1"))
    db_session.commit()

    run_cycle()  # must not raise

    assert _notified(notify_mock) == [("device-1", "BTCUSDT", "BUY", 140.0)]
    btc = db_session.query(Coin).filter_by(symbol="BTCUSDT").one()
    assert btc.pct_below_high_90d is None
