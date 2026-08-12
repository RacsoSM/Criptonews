# backend/app/main.py
from fastapi import FastAPI

from app.db import init_db
from app.routers import devices, coins, signals, candles
from app.scheduler import start_scheduler

app = FastAPI(title="Crypto Signal Notifier")
app.include_router(devices.router)
app.include_router(coins.router)
app.include_router(signals.router)
app.include_router(candles.router)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler(app)


@app.get("/health")
def health():
    return {"status": "ok"}
