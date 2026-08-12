from types import SimpleNamespace

from app.notifications import send_signal_notification


def _fake_signal():
    return SimpleNamespace(coin_symbol="BTCUSDT", signal_type="BUY", price=61000.0)


def test_send_signal_notification_success(mocker):
    mocker.patch("app.notifications._ensure_firebase_initialized", return_value=None)
    mocker.patch("app.notifications.messaging.send", return_value="message-id-123")

    result = send_signal_notification("device-token", _fake_signal())

    assert result is True


def test_send_signal_notification_failure_returns_false(mocker):
    mocker.patch("app.notifications._ensure_firebase_initialized", return_value=None)
    mocker.patch(
        "app.notifications.messaging.send",
        side_effect=Exception("FCM unavailable"),
    )

    result = send_signal_notification("device-token", _fake_signal())

    assert result is False


def test_send_signal_notification_init_failure_returns_false(mocker):
    mocker.patch(
        "app.notifications._ensure_firebase_initialized",
        side_effect=Exception("bad credentials"),
    )
    mocker.patch("app.notifications.messaging.send", return_value="message-id-123")

    result = send_signal_notification("device-token", _fake_signal())

    assert result is False
