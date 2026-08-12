# backend/app/routers/signals.py
from fastapi import APIRouter, Query

from app.db import get_session
from app.models import Signal
from app.schemas import SignalOut

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[SignalOut])
def list_signals(coin_symbol: str | None = Query(default=None)):
    with get_session() as session:
        query = session.query(Signal).order_by(Signal.created_at.desc())
        if coin_symbol is not None:
            query = query.filter_by(coin_symbol=coin_symbol)
        # Convert to SignalOut while the session is still open, since
        # get_session() closes the session on return and ORM attribute
        # access on detached instances would raise DetachedInstanceError.
        return [SignalOut.model_validate(signal) for signal in query.all()]
