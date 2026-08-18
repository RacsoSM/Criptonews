# backend/app/main.py
import logging

from fastapi import FastAPI

from app.db import init_db
from app.routers import devices, coins, signals, candles, entry_score_history, status

# uvicorn configures only its own loggers, leaving the root logger at WARNING —
# so any INFO-level logging from the app would never reach the console without
# this. See backend/scripts/run_cycle.py for the ingestion job's own logging;
# this app is now read-only and only serves the routers below.
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
app.include_router(status.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
