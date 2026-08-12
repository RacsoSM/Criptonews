# backend/app/main.py
from fastapi import FastAPI

from app.db import init_db
from app.routers import devices

app = FastAPI(title="Crypto Signal Notifier")
app.include_router(devices.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
