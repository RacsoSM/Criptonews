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

This only works once this branch is merged into your repo's default branch (`main`) — GitHub only runs scheduled workflows from the default branch.

In the GitHub repo → Settings → Secrets and variables → Actions, add:

- `DATABASE_URL` = the **same** Neon connection string from step 1 (the
  cron job and the API must write to the same database).
- `FIREBASE_SERVICE_ACCOUNT_JSON` = the full contents of
  `backend/firebase-service-account.json` (same file as step 2.7, pasted
  as raw JSON text this time, not a file).

If this repo is private, GitHub gives you 2,000 free Actions minutes/month — this
workflow's hourly runs (~1-2 minutes each) use roughly 730-1,460 minutes/month, which
fits but doesn't leave much headroom. Public repos get unlimited free minutes. Check
your actual usage at Settings → Billing and plans → Actions, and consider making the
repo public if you're close to the cap.

GitHub also auto-disables scheduled workflows after 60 days with no repository
activity (commits, merges, etc.) — it emails you when this happens. If your repo
goes quiet for two months, the hourly job silently stops. Re-enable it from the
Actions tab → the workflow → "Enable workflow", or just push any commit before
that.

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
