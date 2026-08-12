# backend/tests/test_scheduler_job.py
from contextlib import contextmanager
from types import SimpleNamespace

import pandas as pd

from app.models import Coin, DeviceToken
from app.scheduler import run_cycle


def _session_ctx(session):
    @contextmanager
    def _ctx():
        yield session

    return _ctx()


def _fake_klines_df():
    closes = [100.0 + i for i in range(40)]
    return pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
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
    notify_mock.assert_called_once_with("device-1", fake_signal)


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
    assert notify_mock.call_args_list == [
        mocker.call("device-1", btc_signal),
        mocker.call("device-2", btc_signal),
        mocker.call("device-1", eth_signal),
        mocker.call("device-2", eth_signal),
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
    notify_mock.assert_called_once_with("device-1", eth_signal)
    # And the cycle's coin-table refresh survived (session was not rolled back).
    assert db_session.query(Coin).filter_by(symbol="ETHUSDT").count() == 1


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


def test_start_scheduler_registers_hourly_job_and_stores_scheduler(mocker):
    from app.scheduler import start_scheduler

    scheduler_instance = mocker.Mock()
    scheduler_cls = mocker.patch(
        "app.scheduler.BackgroundScheduler", return_value=scheduler_instance
    )
    app = SimpleNamespace(state=SimpleNamespace())

    start_scheduler(app)

    scheduler_cls.assert_called_once_with()
    assert scheduler_instance.add_job.call_count == 1
    args, kwargs = scheduler_instance.add_job.call_args
    assert args[0] is run_cycle
    assert args[1] == "cron"
    assert kwargs == {"minute": 1}
    scheduler_instance.start.assert_called_once_with()
    assert app.state.scheduler is scheduler_instance
