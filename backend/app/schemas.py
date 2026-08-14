# backend/app/schemas.py
from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


def _assume_utc(value: datetime | None) -> datetime | None:
    """Stamp UTC onto a naive datetime coming out of the database.

    Every timestamp is written as `datetime.now(timezone.utc)`, but SQLite
    stores it in a naive `DateTime` column and hands it back without a
    timezone. Serialized as-is, the JSON would carry no offset (
    `2026-08-12T19:00:52`) and any client — notably the Android app — would
    parse it as local time and render every signal hours off. Attaching the
    offset the values already implicitly have costs no migration.
    """
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class CoinOut(BaseModel):
    symbol: str
    name: str
    rank: int
    has_open_position: bool
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    image_url: str | None = None
    current_price: float | None = None
    entry_score: float | None = None
    pct_below_high_90d: float | None = None
    pct_below_high_180d: float | None = None
    pct_below_high_360d: float | None = None


class PositionOut(BaseModel):
    id: int
    coin_symbol: str
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    status: str
    closed_price: float | None
    closed_time: datetime | None

    class Config:
        from_attributes = True

    @field_validator("entry_time", "closed_time")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        return _assume_utc(value)


class SignalOut(BaseModel):
    id: int
    coin_symbol: str
    signal_type: str
    price: float
    rsi_vote: str | None
    ema_cross_vote: str | None
    macd_vote: str | None
    donchian_vote: str | None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("created_at")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return _assume_utc(value)


class DeviceTokenIn(BaseModel):
    token: str


class EntryScoreHistoryOut(BaseModel):
    score: float
    computed_at: datetime

    class Config:
        from_attributes = True

    @field_validator("computed_at")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return _assume_utc(value)


class CandleOut(BaseModel):
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    ema_9: float | None = None
    ema_21: float | None = None
    rsi_14: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    donchian_upper: float | None = None
    donchian_lower: float | None = None
