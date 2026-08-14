# backend/app/routers/entry_score_history.py
from fastapi import APIRouter

from app.db import get_session
from app.models import EntryScoreHistory
from app.schemas import EntryScoreHistoryOut

router = APIRouter(prefix="/coins", tags=["entry_score_history"])


@router.get("/{symbol}/entry-score-history", response_model=list[EntryScoreHistoryOut])
def get_entry_score_history(symbol: str, limit: int = 168):
    with get_session() as session:
        # Newest-first for the LIMIT to grab the most recent window, then
        # reversed so the response reads oldest-to-newest — the order a line
        # chart draws left-to-right.
        rows = (
            session.query(EntryScoreHistory)
            .filter_by(coin_symbol=symbol)
            .order_by(EntryScoreHistory.computed_at.desc())
            .limit(limit)
            .all()
        )
        # Convert to EntryScoreHistoryOut while the session is still open,
        # since get_session() closes the session on return and ORM attribute
        # access on detached instances would raise DetachedInstanceError.
        return [EntryScoreHistoryOut.model_validate(row) for row in reversed(rows)]
