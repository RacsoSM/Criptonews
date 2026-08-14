# backend/app/main.py
import logging

from fastapi import FastAPI

from app.db import init_db
from app.routers import devices, coins, signals, candles, entry_score_history
from app.scheduler import start_scheduler

# uvicorn configures only its own loggers, leaving the root logger at WARNING —
# so the scheduler's per-cycle INFO summary would never reach the console
# without this. Verified: with uvicorn's LOGGING_CONFIG applied and no
# basicConfig, `logging.getLogger("app.scheduler").isEnabledFor(INFO)` is False.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Crypto Signal Notifier")
app.include_router(devices.router)
app.include_router(coins.router)
app.include_router(signals.router)
app.include_router(candles.router)
app.include_router(entry_score_history.router)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler(app)


@app.on_event("shutdown")
def on_shutdown():
    """Stop the background scheduler when the app goes down.

    Without this, every process that ever started the app (tests using
    `TestClient` as a context manager, each `uvicorn --reload` restart) leaves
    a live `BackgroundScheduler` behind whose cron trigger would fire real
    CoinGecko/Binance/Firebase calls against the real DB at HH:01.
    `getattr` guards the case where shutdown runs without a successful
    startup.
    """
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health():
    return {"status": "ok"}
