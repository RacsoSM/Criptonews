# Cloud Deployment (GitHub Actions Cron + Hosted Backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop depending on the user's PC/local wifi to run the app: move the hourly ingestion cycle to a GitHub Actions cron job, host the FastAPI backend on a public URL, and point it at an externally hosted Postgres database.

**Architecture:** The in-process APScheduler currently wired into `app.main`'s FastAPI lifecycle is removed. A new standalone script (`backend/scripts/run_cycle.py`) wraps the existing, already-tested `run_cycle()` function so GitHub Actions can invoke it on a cron schedule against an external Postgres DB. The FastAPI app itself becomes read-only from the ingestion job's perspective — it only serves `/coins`, `/signals`, `/candles`, `/entry-score-history`, etc. to the Android app — and gets deployed to a free host (Render) with a public URL, so the DB and API are reachable from anywhere, not just the user's LAN.

**Tech Stack:** FastAPI, SQLAlchemy (already DB-agnostic via `DATABASE_URL`), GitHub Actions (`schedule` trigger), Postgres (Neon or Supabase free tier), Render (free web service), existing Firebase Admin SDK for FCM (unchanged).

**Spec:** No separate spec doc — requirements were established via conversation: (1) no cost beyond free tiers, no credit card anywhere, (2) don't restructure the existing stack (SQLite/SQLAlchemy → Postgres/SQLAlchemy is a config change, not a rewrite; Firebase stays exactly as-is, used only for FCM), (3) the app must be reachable without the user's PC being on or on a specific wifi network.

## Global Constraints

- No paid tier or credit-card-gated service anywhere in the chain (GitHub Actions free minutes, Render free web service, Neon/Supabase free Postgres).
- `firebase-service-account.json` / FCM behavior must not change — same credentials, same `app/notifications.py`.
- `DATABASE_URL` must keep working for both `sqlite:///./cryptonews.db` (local dev, existing tests) and a Postgres URL (production) with zero code branching beyond what `app/db.py` already does.
- Existing test suite (`backend/tests/`) must keep passing after every task.
- Only one process may ever call `run_cycle()` per hour — never both an in-process scheduler and GitHub Actions at once (double-processing would double-send push notifications and skew the entry-score history).

---

## File Structure

- `backend/scripts/__init__.py` — new, makes `scripts` an importable package (mirrors `app/__init__.py`).
- `backend/scripts/run_cycle.py` — new, the entrypoint GitHub Actions runs: `init_db()` then `run_cycle()`. Thin wrapper only — all real logic stays in `app/scheduler.py`, untouched.
- `backend/tests/test_run_cycle_script.py` — new, verifies the wrapper calls both functions.
- `backend/app/main.py` — modified, drops the `start_scheduler`/`on_shutdown` wiring since GitHub Actions now owns the cron.
- `backend/app/scheduler.py` — modified, drops `start_scheduler()` and its now-unused `BackgroundScheduler`/`FastAPI` imports; `run_cycle()` itself is untouched.
- `backend/tests/test_main.py` — modified, drops the scheduler-lifecycle tests that no longer apply.
- `backend/requirements.txt` — modified, drops `apscheduler`, adds `psycopg2-binary` (Postgres driver for production).
- `.github/workflows/hourly-cycle.yml` — new, the cron workflow.
- `docs/deployment.md` — new, exact manual steps for the user (Neon/Supabase, Render, GitHub secrets, Android `BASE_URL` update) — these steps require the user's own accounts and can't be done by an agent.

---

### Task 1: Standalone `run_cycle` entrypoint script

**Files:**
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/run_cycle.py`
- Test: `backend/tests/test_run_cycle_script.py`

**Interfaces:**
- Consumes: `app.db.init_db() -> None`, `app.scheduler.run_cycle() -> None` (both already exist, unchanged).
- Produces: `scripts.run_cycle.main() -> None`, importable as `python -m scripts.run_cycle` when run with cwd `backend/` (matches how `backend/tests/` already imports `app.*` with cwd `backend/`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_run_cycle_script.py`:

```python
from scripts import run_cycle as run_cycle_script


def test_main_initializes_db_then_runs_one_cycle(mocker):
    init_db_mock = mocker.patch("scripts.run_cycle.init_db")
    run_cycle_mock = mocker.patch("scripts.run_cycle.run_cycle")

    run_cycle_script.main()

    init_db_mock.assert_called_once()
    run_cycle_mock.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `pytest tests/test_run_cycle_script.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts'`

- [ ] **Step 3: Create the package and the script**

Create `backend/scripts/__init__.py` (empty file).

Create `backend/scripts/run_cycle.py`:

```python
"""Standalone entrypoint for running one ingestion cycle outside the API process.

Invoked by the GitHub Actions hourly workflow (.github/workflows/hourly-cycle.yml),
which owns the schedule now that the backend no longer runs a resident process —
see app/main.py for why the in-process APScheduler was removed.
"""
from app.db import init_db
from app.scheduler import run_cycle


def main() -> None:
    init_db()
    run_cycle()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `pytest tests/test_run_cycle_script.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/__init__.py backend/scripts/run_cycle.py backend/tests/test_run_cycle_script.py
git commit -m "feat: add standalone run_cycle entrypoint for GitHub Actions"
```

---

### Task 2: Remove the in-process scheduler from the FastAPI app

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/scheduler.py`
- Modify: `backend/tests/test_main.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `app.main.app` with only a startup hook that calls `init_db()`; no `on_shutdown`, no `app.state.scheduler`. `app.scheduler.run_cycle` keeps its existing signature — Task 1's script is the only caller left.

- [ ] **Step 1: Update the test first (it currently asserts behavior we're deleting)**

Replace `backend/tests/test_main.py` entirely with:

```python
# backend/tests/test_main.py
from fastapi.testclient import TestClient

from app.main import app


def test_app_starts_and_root_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `pytest tests/test_main.py -v`
Expected: FAIL — the old `app.main.start_scheduler` still runs a real `BackgroundScheduler` on startup, but that's not why it fails; it fails because `app.main` still references the now-mocked-away symbols the old tests patched. (If it happens to pass as-is, that's fine too — proceed to Step 3 regardless, since the goal is the code change, not a red test for its own sake.)

- [ ] **Step 3: Simplify `app/main.py`**

Replace `backend/app/main.py` entirely with:

```python
# backend/app/main.py
import logging

from fastapi import FastAPI

from app.db import init_db
from app.routers import devices, coins, signals, candles, entry_score_history

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


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Drop the now-unused `start_scheduler` from `app/scheduler.py`**

In `backend/app/scheduler.py`:
- Remove the import `from apscheduler.schedulers.background import BackgroundScheduler`.
- Remove the import `from fastapi import FastAPI`.
- Remove the `start_scheduler(app: FastAPI) -> None` function at the bottom of the file (the last 5 lines).

Everything else in `scheduler.py` (`run_cycle` and its helpers) stays exactly as-is — it's still fully covered by `backend/tests/test_scheduler_job.py`, unchanged.

- [ ] **Step 5: Drop the now-unused `apscheduler` dependency**

In `backend/requirements.txt`, remove the line `apscheduler==3.10.4`.

- [ ] **Step 6: Run the test to verify it passes**

Run (from `backend/`): `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 7: Run the full backend test suite to confirm nothing else broke**

Run (from `backend/`): `pytest -v`
Expected: All tests PASS (in particular `tests/test_scheduler_job.py`, which tests `run_cycle` directly and doesn't touch `start_scheduler`).

- [ ] **Step 8: Commit**

```bash
git add backend/app/main.py backend/app/scheduler.py backend/tests/test_main.py backend/requirements.txt
git commit -m "refactor: remove in-process scheduler, GitHub Actions now owns the hourly cron"
```

---

### Task 3: Add the Postgres driver for production

**Files:**
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: nothing.
- Produces: `psycopg2` importable, so `DATABASE_URL=postgresql://...` works with SQLAlchemy in both the Render-hosted API and the GitHub Actions job. `sqlite:///...` keeps working unchanged for local dev and the existing test suite (`app/db.py`'s `create_engine` call is already driver-agnostic — see `backend/app/db.py:8-11`).

- [ ] **Step 1: Add the dependency**

In `backend/requirements.txt`, add a line:

```
psycopg2-binary==2.9.9
```

- [ ] **Step 2: Install and verify it doesn't break the existing suite**

Run (from `backend/`):
```bash
pip install -r requirements.txt
pytest -v
```
Expected: install succeeds, all tests still PASS (tests use `sqlite:///:memory:` via `conftest.py`, unaffected by adding a driver for a different DB backend).

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "build: add psycopg2 for production Postgres support"
```

---

### Task 4: GitHub Actions hourly workflow

**Files:**
- Create: `.github/workflows/hourly-cycle.yml`

**Interfaces:**
- Consumes: `backend/scripts/run_cycle.py` (Task 1), repo secrets `DATABASE_URL` and `FIREBASE_SERVICE_ACCOUNT_JSON` (created manually by the user — see Task 5's `docs/deployment.md`).
- Produces: an hourly run of the full ingestion cycle against the production DB, independent of any server staying alive.

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/hourly-cycle.yml`:

```yaml
name: Hourly ingestion cycle

on:
  schedule:
    # Runs a few minutes past the hour, after Binance's 1h candle closes.
    # GitHub's scheduler is best-effort and can drift a few minutes — that's
    # fine here since we always pull the last 100 candles, not just the
    # newest one.
    - cron: "5 * * * *"
  workflow_dispatch: {}

jobs:
  run-cycle:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Write Firebase service account credentials
        run: echo "$FIREBASE_SERVICE_ACCOUNT_JSON" > firebase-service-account.json
        env:
          FIREBASE_SERVICE_ACCOUNT_JSON: ${{ secrets.FIREBASE_SERVICE_ACCOUNT_JSON }}

      - name: Run ingestion cycle
        run: python -m scripts.run_cycle
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          FIREBASE_CREDENTIALS_PATH: ./firebase-service-account.json
          TOP_N_COINS: "30"
```

- [ ] **Step 2: Validate the YAML is well-formed**

Run (from repo root):
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/hourly-cycle.yml'))"
```
Expected: no output, no exception (confirms valid YAML syntax; the workflow's actual behavior can only be verified after Task 5's secrets exist — see `docs/deployment.md`'s verification step).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/hourly-cycle.yml
git commit -m "ci: run the ingestion cycle hourly via GitHub Actions"
```

---

### Task 5: Manual deployment guide

**Files:**
- Create: `docs/deployment.md`

**Interfaces:**
- Consumes: nothing (pure documentation).
- Produces: an exact, copy-pasteable checklist the user follows in their own Neon/Supabase, Render, and GitHub accounts — none of these steps can be performed by an agent since they require the user's own credentials and account ownership decisions.

- [ ] **Step 1: Write the guide**

Create `docs/deployment.md`:

```markdown
# Deployment guide

Moves the backend off your PC/LAN onto free-tier cloud hosting. No paid
tier or credit card required anywhere in this guide.

## 1. Create the Postgres database (Neon)

1. Sign up at https://neon.tech (free tier, no card required).
2. Create a new project. Note the connection string it gives you — it
   looks like `postgresql://user:password@host/dbname?sslmode=require`.
   This is your `DATABASE_URL`.

(Supabase's free Postgres works the same way if you'd rather use that —
its connection string is in Project Settings → Database.)

## 2. Deploy the backend API (Render)

1. Sign up at https://render.com (free tier, no card required) and
   connect your GitHub account.
2. New → Web Service → pick this repo.
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables (Render dashboard → Environment):
   - `DATABASE_URL` = the Neon connection string from step 1
   - `FIREBASE_CREDENTIALS_PATH` = `/etc/secrets/firebase-service-account.json`
7. Add a Secret File (Render dashboard → Environment → Secret Files):
   - Filename: `firebase-service-account.json`
   - Contents: paste the full contents of `backend/firebase-service-account.json`
   - Render mounts it at `/etc/secrets/firebase-service-account.json`,
     matching `FIREBASE_CREDENTIALS_PATH` above.
8. Deploy. Render gives you a public URL like
   `https://criptonews-backend.onrender.com`. Save it — you need it in
   step 4 below.

Render's free tier sleeps after inactivity; the first request after a
sleep takes a few extra seconds to wake it up. That's expected and fine
for a mobile app.

## 3. Wire up the GitHub Actions cron job

In the GitHub repo → Settings → Secrets and variables → Actions, add:

- `DATABASE_URL` = the **same** Neon connection string from step 1 (the
  cron job and the API must write to the same database).
- `FIREBASE_SERVICE_ACCOUNT_JSON` = the full contents of
  `backend/firebase-service-account.json` (same file as step 2.7, pasted
  as raw JSON text this time, not a file).

Verify it: Actions tab → "Hourly ingestion cycle" → Run workflow (uses
the `workflow_dispatch` trigger, no need to wait for the next hour).
Check the run's logs for the "Cycle complete: N coins processed..." line
logged by `run_cycle()` (see `backend/app/scheduler.py`).

## 4. Point the Android app at the public URL

In `android/app/build.gradle.kts`, update the `BASE_URL` field to your
Render URL from step 2.8:

```kotlin
buildConfigField("String", "BASE_URL", "\"https://criptonews-backend.onrender.com/\"")
```

Rebuild the app. It now works on any network, not just your home wifi.
```

- [ ] **Step 2: Commit**

```bash
git add docs/deployment.md
git commit -m "docs: add cloud deployment guide"
```

---

## Self-Review

**Spec coverage:**
- No cost/no credit card → Neon, Render, GitHub Actions are all free-tier, called out explicitly in `docs/deployment.md`. ✓
- Don't restructure the stack → SQLAlchemy/DB layer untouched beyond the driver; Firebase untouched; only the scheduler's trigger moved. ✓
- Reachable without the user's PC/wifi → Render gives a public URL (Task 5), Actions runs independent of any local machine (Task 4). ✓
- Avoid double-processing → Task 2 removes the in-process scheduler so GitHub Actions is the only trigger, called out in Global Constraints. ✓

**Placeholder scan:** No TBDs; all code blocks are complete and copy-pasteable; `docs/deployment.md`'s Render URL example is clearly an example, with the actual substitution spelled out as a literal step.

**Type consistency:** `scripts.run_cycle.main()` takes no args, returns `None`, matches the only caller (the GitHub Actions `python -m scripts.run_cycle` invocation). `init_db()` and `run_cycle()` signatures are unchanged from their current definitions in `app/db.py` and `app/scheduler.py`.
