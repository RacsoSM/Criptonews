# backend/tests/test_main.py
from fastapi.testclient import TestClient

from app.main import app


def test_app_starts_and_root_health_check(mocker):
    # Never let a real BackgroundScheduler (live cron -> real HTTP + real DB)
    # escape into the test run.
    mocker.patch("app.main.start_scheduler")

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_shutdown_stops_the_scheduler(mocker):
    """The startup hook must have a matching shutdown hook.

    Otherwise every started process (tests, each `uvicorn --reload` restart)
    leaks a live scheduler whose cron would fire real API calls at HH:01.
    """
    scheduler = mocker.Mock()
    mocker.patch(
        "app.main.start_scheduler",
        side_effect=lambda a: setattr(a.state, "scheduler", scheduler),
    )

    with TestClient(app):
        scheduler.shutdown.assert_not_called()

    scheduler.shutdown.assert_called_once_with(wait=False)


def test_shutdown_is_safe_when_startup_never_stored_a_scheduler(mocker):
    mocker.patch("app.main.start_scheduler")
    app.state._state.pop("scheduler", None)

    with TestClient(app):
        pass  # must not raise on the way out
