# backend/tests/test_models.py
from datetime import datetime, timezone

from app.models import Coin, Signal, Position, DeviceToken, EntryScoreHistory


def test_coin_model_fields(db_session):
    coin = Coin(symbol="BTCUSDT", name="Bitcoin", rank=1, active=True)
    db_session.add(coin)
    db_session.flush()
    assert coin.id is not None
    assert coin.symbol == "BTCUSDT"


def test_position_model_defaults(db_session):
    position = Position(
        coin_symbol="BTCUSDT",
        entry_price=60000.0,
        entry_time=datetime.now(timezone.utc),
        stop_loss=57000.0,
        take_profit=66000.0,
    )
    db_session.add(position)
    db_session.flush()
    assert position.status == "OPEN"
    assert position.closed_price is None


def test_signal_model_links_to_position(db_session):
    position = Position(
        coin_symbol="ETHUSDT",
        entry_price=3000.0,
        entry_time=datetime.now(timezone.utc),
        stop_loss=2800.0,
        take_profit=3400.0,
    )
    db_session.add(position)
    db_session.flush()

    signal = Signal(
        coin_symbol="ETHUSDT",
        signal_type="BUY",
        price=3000.0,
        rsi_vote="buy",
        ema_cross_vote="buy",
        macd_vote="buy",
        donchian_vote=None,
        created_at=datetime.now(timezone.utc),
        position_id=position.id,
    )
    db_session.add(signal)
    db_session.flush()
    assert signal.position_id == position.id


def test_device_token_unique(db_session):
    token = DeviceToken(token="abc123")
    db_session.add(token)
    db_session.flush()
    assert token.id is not None


def test_entry_score_history_model_fields(db_session):
    entry = EntryScoreHistory(coin_symbol="BTCUSDT", score=42.5)
    db_session.add(entry)
    db_session.flush()
    assert entry.id is not None
    assert entry.computed_at is not None
