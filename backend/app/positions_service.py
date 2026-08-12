# backend/app/positions_service.py
"""Position lifecycle orchestration.

Implements the holding strategy's state machine: a coin has at most one OPEN
`Position` at a time. A BUY signal opens one (only when none is open), the
opposing SELL signal closes it (only when one is open); every other
combination is a no-op. Stop loss / take profit are recorded at entry as
*informational reference levels only* — nothing in this module (or the rest
of the system) closes a position because price reached them.

This module never calls `session.commit()`: the caller owns the transaction
boundary (see `app.db.get_session`). It only `add`s and `flush`es so that
generated primary keys are available to the caller.
"""

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.indicators import atr
from app.models import Position, Signal
from app.signal_engine import IndicatorVotes, compute_votes, decide_direction

# Informational-only ATR multiples applied at entry time.
STOP_LOSS_ATR_MULTIPLE = 1.5
TAKE_PROFIT_ATR_MULTIPLE = 3.0


def _build_signal(
    symbol: str,
    signal_type: str,
    price: float,
    votes: IndicatorVotes,
    created_at: datetime,
    position_id: int | None,
) -> Signal:
    return Signal(
        coin_symbol=symbol,
        signal_type=signal_type,
        price=price,
        rsi_vote=votes.rsi,
        ema_cross_vote=votes.ema_cross,
        macd_vote=votes.macd,
        donchian_vote=votes.donchian,
        created_at=created_at,
        position_id=position_id,
    )


def process_coin(session: Session, symbol: str, df: pd.DataFrame) -> Signal | None:
    """Run one decision cycle for `symbol` against its OHLC frame `df`.

    Returns the persisted `Signal` row when a position was opened or closed,
    and `None` when nothing happened — no direction, a BUY while already
    holding, or a SELL while flat. When `None` is returned no rows are
    written at all.
    """
    votes = compute_votes(df)
    direction = decide_direction(votes)
    if direction is None:
        return None

    open_position = (
        session.query(Position)
        .filter_by(coin_symbol=symbol, status="OPEN")
        .one_or_none()
    )
    current_price = float(df["close"].iloc[-1])
    now = datetime.now(timezone.utc)

    if direction == "BUY":
        if open_position is not None:
            # Already holding this coin — hold, do not stack positions.
            return None
        atr_value = float(atr(df["high"], df["low"], df["close"]).iloc[-1])
        position = Position(
            coin_symbol=symbol,
            entry_price=current_price,
            entry_time=now,
            stop_loss=current_price - STOP_LOSS_ATR_MULTIPLE * atr_value,
            take_profit=current_price + TAKE_PROFIT_ATR_MULTIPLE * atr_value,
            status="OPEN",
        )
        session.add(position)
        session.flush()  # assigns position.id for the Signal FK
        signal = _build_signal(symbol, "BUY", current_price, votes, now, position.id)
        session.add(signal)
        session.flush()
        return signal

    if direction == "SELL":
        if open_position is None:
            # Nothing held for this coin — never sell what we don't hold.
            return None
        open_position.status = "CLOSED"
        open_position.closed_price = current_price
        open_position.closed_time = now
        signal = _build_signal(
            symbol, "SELL", current_price, votes, now, open_position.id
        )
        session.add(signal)
        session.flush()
        return signal

    return None
