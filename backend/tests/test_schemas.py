# backend/tests/test_schemas.py
"""Timestamps leaving the API must carry an explicit UTC offset.

Every timestamp is written as `datetime.now(timezone.utc)`, but SQLite's
`DateTime` column drops the tzinfo, so the ORM hands back naive values that are
in fact UTC. Serialized as-is they would be offset-less
(`"2026-08-12T19:00:52"`), and any client — the Android app in particular —
would parse them as local time.
"""
from datetime import datetime, timezone

from app.schemas import PositionOut, SignalOut

NAIVE = datetime(2026, 8, 12, 19, 0, 52, 306234)  # naive, but really UTC
UTC_MARKERS = ("Z", "+00:00")


def _has_utc_offset(iso: str) -> bool:
    return iso.endswith(UTC_MARKERS)


def _signal(created_at: datetime) -> SignalOut:
    return SignalOut(
        id=1,
        coin_symbol="BTCUSDT",
        signal_type="BUY",
        price=60000.0,
        rsi_vote="buy",
        ema_cross_vote="buy",
        macd_vote="buy",
        donchian_vote=None,
        created_at=created_at,
    )


def _position(entry_time: datetime, closed_time: datetime | None) -> PositionOut:
    return PositionOut(
        id=1,
        coin_symbol="BTCUSDT",
        entry_price=60000.0,
        entry_time=entry_time,
        stop_loss=57000.0,
        take_profit=66000.0,
        status="CLOSED" if closed_time else "OPEN",
        closed_price=61000.0 if closed_time else None,
        closed_time=closed_time,
    )


def test_signal_out_naive_created_at_serializes_with_utc_offset():
    payload = _signal(NAIVE).model_dump(mode="json")

    assert _has_utc_offset(payload["created_at"]), payload["created_at"]
    assert payload["created_at"].startswith("2026-08-12T19:00:52")  # value unchanged


def test_signal_out_json_string_carries_the_offset():
    body = _signal(NAIVE).model_dump_json()

    assert '"created_at":"2026-08-12T19:00:52.306234Z"' in body or (
        '"created_at":"2026-08-12T19:00:52.306234+00:00"' in body
    ), body


def test_position_out_naive_timestamps_serialize_with_utc_offset():
    payload = _position(NAIVE, NAIVE).model_dump(mode="json")

    assert _has_utc_offset(payload["entry_time"]), payload["entry_time"]
    assert _has_utc_offset(payload["closed_time"]), payload["closed_time"]


def test_position_out_null_closed_time_stays_null():
    payload = _position(NAIVE, None).model_dump(mode="json")

    assert payload["closed_time"] is None


def test_already_aware_timestamps_are_left_alone():
    aware = datetime(2026, 8, 12, 19, 0, 52, tzinfo=timezone.utc)

    assert _signal(aware).created_at == aware
    assert _has_utc_offset(_signal(aware).model_dump(mode="json")["created_at"])
