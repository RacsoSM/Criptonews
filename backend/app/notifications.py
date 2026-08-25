"""Firebase Cloud Messaging (FCM) push notification wrapper.

Sends a push notification for a generated Signal. Never raises: any
failure (bad credentials, network error, invalid token, Firebase Admin
SDK initialization failure) is caught and results in a `False` return,
so callers (e.g. the scheduler) can log and continue without crashing
the cycle. The signal itself is always persisted independently of
whether the notification succeeds.
"""
import firebase_admin
from firebase_admin import credentials, messaging

from app.config import settings


def _ensure_firebase_initialized() -> None:
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred)


def send_signal_notification(token: str, signal) -> bool:
    try:
        _ensure_firebase_initialized()
        title = f"{signal.signal_type} {signal.coin_symbol}"
        body = f"Precio: {signal.price:.2f} USDT"
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={"coin_symbol": signal.coin_symbol, "signal_type": signal.signal_type},
            token=token,
        )
        messaging.send(message)
        return True
    except Exception:
        return False


def send_entry_score_notification(token: str, notice) -> bool:
    """Alert that a coin's buy-entry score crossed `notice.threshold` (60 or 80).

    Independent of `send_signal_notification`: this fires on the continuous
    entry score (`app.entry_score`) crossing a threshold, not on an actual
    BUY/SELL signal, so a coin can trigger this well before (or without ever)
    producing a real signal.
    """
    try:
        _ensure_firebase_initialized()
        title = f"Oportunidad {notice.threshold}%: {notice.coin_symbol}"
        body = f"Score de entrada de {notice.coin_symbol} superó el {notice.threshold}% ({notice.score:.1f})"
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={
                "coin_symbol": notice.coin_symbol,
                "entry_score": str(notice.score),
                "threshold": str(notice.threshold),
            },
            token=token,
        )
        messaging.send(message)
        return True
    except Exception:
        return False
