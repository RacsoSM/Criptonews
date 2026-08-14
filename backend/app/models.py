# backend/app/models.py
from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Coin(Base):
    __tablename__ = "coins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    rank: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_below_high_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_below_high_180d: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_below_high_360d: Mapped[float | None] = mapped_column(Float, nullable=True)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coin_symbol: Mapped[str] = mapped_column(String, index=True)
    entry_price: Mapped[float] = mapped_column(Float)
    entry_time: Mapped[datetime] = mapped_column(DateTime)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # OPEN | CLOSED
    closed_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    closed_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coin_symbol: Mapped[str] = mapped_column(String, index=True)
    signal_type: Mapped[str] = mapped_column(String)  # BUY | SELL
    price: Mapped[float] = mapped_column(Float)
    rsi_vote: Mapped[str | None] = mapped_column(String, nullable=True)
    ema_cross_vote: Mapped[str | None] = mapped_column(String, nullable=True)
    macd_vote: Mapped[str | None] = mapped_column(String, nullable=True)
    donchian_vote: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), nullable=True)


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
