# backend/app/routers/status.py
from fastapi import APIRouter
from sqlalchemy import func

from app.db import get_session
from app.models import EntryScoreHistory
from app.schemas import StatusOut

router = APIRouter(tags=["status"])


@router.get("/status", response_model=StatusOut)
def get_status():
    with get_session() as session:
        # EntryScoreHistory gets a row per active coin every cycle (see
        # scheduler.run_cycle), so its max computed_at is a reliable proxy
        # for "when did the last ingestion cycle run" without needing a
        # dedicated run-log table.
        last_updated = session.query(func.max(EntryScoreHistory.computed_at)).scalar()
        return StatusOut(last_updated=last_updated)
