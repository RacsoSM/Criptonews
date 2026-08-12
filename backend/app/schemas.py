# backend/app/schemas.py
from datetime import datetime

from pydantic import BaseModel


class CoinOut(BaseModel):
    symbol: str
    name: str
    rank: int
    has_open_position: bool
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


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


class DeviceTokenIn(BaseModel):
    token: str


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
