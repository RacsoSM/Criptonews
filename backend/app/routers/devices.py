# backend/app/routers/devices.py
from fastapi import APIRouter, status

from app.db import get_session
from app.models import DeviceToken
from app.schemas import DeviceTokenIn

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceTokenIn):
    with get_session() as session:
        existing = session.query(DeviceToken).filter_by(token=payload.token).one_or_none()
        if existing is None:
            session.add(DeviceToken(token=payload.token))
    return {"status": "registered"}
