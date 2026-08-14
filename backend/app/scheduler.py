# backend/app/scheduler.py
"""Hourly cycle orchestration.

`run_cycle()` is the single job that ties the whole backend together:

1. Refresh the tracked coin list from the top-N ranking (upsert, never delete).
2. For each coin in this cycle's work list, fetch fresh 1h candles.
3. Hand them to `process_coin`, which owns all position/signal logic.
4. Push every generated signal to every registered device token — but only
   once the cycle's transaction has actually committed (see below).

The work list is the UNION of the current top-N ranking and every coin still
holding an OPEN position. A coin that drops out of the ranking while holding a
position must keep being analysed, otherwise the engine could never produce the
SELL that closes it and the position would be stranded forever.

Notifications are deliberately NOT sent inside the session block. A push is
irreversible; the transaction is not. If a later coin trips the flush-level
abort path (or the closing commit fails), every signal in the cycle is rolled
back — so a notification sent mid-loop would advertise a signal that does not
exist in the database and never shows up in `/signals`. The loop therefore only
collects detached, plain-data snapshots (the ORM rows are unusable once the
session closes) and the sends happen after the `with` block exits cleanly.

The whole cycle runs inside ONE `get_session()` transaction, so a single
coin's failure must never be allowed to escape the `with` block: `get_session`
rolls back on any exception, which would discard every other coin's
legitimately computed signals and position updates. Every per-coin step is
therefore individually guarded.

The boundary of that guarantee is worth stating precisely, because it is
narrower than "any one coin can fail safely":

* Exceptions raised by `process_coin`'s own logic (bad candle data, a
  `Multiple rows were found`, an arithmetic error…) leave the session's
  transaction intact. Those coins are logged and skipped, and every other
  coin's work is still committed at the end of the cycle.
* A failure at the transaction level — a `session.flush()` blowing up with
  `OperationalError: database is locked` or an `IntegrityError` — deactivates
  the session's transaction. Nothing further can be flushed, so continuing
  would only produce a `PendingRollbackError` per remaining coin, burying the
  real root cause under ~29 misleading tracebacks, and `get_session`'s final
  `commit()` would fail regardless. In that case the cycle logs one ERROR,
  rolls back and aborts the remaining coins.

This module contains no indicator math, no HTTP client logic and no
position-state logic; it only sequences the modules that own those.
"""

import logging
from types import SimpleNamespace

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.config import settings
from app.db import get_session
from app.entry_score import compute_entry_score
from app.indicators import pct_below_high
from app.market_data import get_klines, get_top_symbols
from app.models import Coin, DeviceToken, EntryScoreHistory, Position
from app.notifications import send_signal_notification
from app.positions_service import process_coin

logger = logging.getLogger(__name__)


def _refresh_coins(session, top_symbols: list[dict]) -> None:
    """Upsert the top-N ranking into the `coins` table.

    Coins that dropped out of the ranking are deactivated, never deleted, so
    their historical positions and signals keep a resolvable symbol.
    """
    existing = {c.symbol: c for c in session.query(Coin).all()}
    for entry in top_symbols:
        coin = existing.get(entry["symbol"])
        if coin is not None:
            coin.name = entry["name"]
            coin.rank = entry["rank"]
            coin.active = True
            coin.image_url = entry.get("image_url")
        else:
            session.add(Coin(
                symbol=entry["symbol"],
                name=entry["name"],
                rank=entry["rank"],
                active=True,
                image_url=entry.get("image_url"),
            ))

    current_symbols = {e["symbol"] for e in top_symbols}
    for symbol, coin in existing.items():
        if symbol not in current_symbols:
            coin.active = False

    session.flush()


def _cycle_symbols(session, top_symbols: list[dict]) -> list[str]:
    """The coins to analyse this cycle: the ranking plus any open position.

    A coin that fell out of the top-N but still holds an OPEN position stays on
    the list. Dropping it would leave the position permanently open, because
    only a technical SELL — which requires analysing the coin — can close it.
    """
    symbols = [entry["symbol"] for entry in top_symbols]
    tracked = set(symbols)

    still_open = (
        session.query(Position.coin_symbol)
        .filter_by(status="OPEN")
        .distinct()
        .order_by(Position.coin_symbol)
        .all()
    )
    for (symbol,) in still_open:
        if symbol not in tracked:
            tracked.add(symbol)
            symbols.append(symbol)
            logger.info(
                "%s is outside the top-%d ranking but holds an OPEN position — "
                "still monitoring it this cycle",
                symbol,
                settings.top_n_coins,
            )

    return symbols


def _notify_all(device_tokens: list[str], signal) -> int:
    """Push `signal` to every registered token; return how many sends succeeded.

    `send_signal_notification` never raises and never logs — it swallows bad
    credentials, network errors and invalid tokens alike and just returns
    `False`. Without the warning below, a misconfigured Firebase setup would
    silently deliver nothing forever. The exception guard is belt-and-braces:
    a failure here must never cost us the cycle's (already committed) DB work.
    """
    sent = 0
    for token in device_tokens:
        try:
            if send_signal_notification(token, signal):
                sent += 1
            else:
                logger.warning(
                    "FCM send returned failure for token ending %s (%s %s) — "
                    "check Firebase credentials and token validity",
                    token[-6:],
                    signal.signal_type,
                    signal.coin_symbol,
                )
        except Exception:
            logger.exception(
                "Notification failed for token ending %s (%s %s)",
                token[-6:],
                signal.signal_type,
                signal.coin_symbol,
            )
    return sent


def run_cycle() -> None:
    device_tokens: list[str] = []
    pending_notifications: list[SimpleNamespace] = []
    coins_processed = 0
    signals_generated = 0
    notifications_sent = 0
    aborted = False

    with get_session() as session:
        try:
            top_symbols = get_top_symbols(limit=settings.top_n_coins)
        except Exception as exc:
            # No coin list means nothing to process — abort the cycle cleanly.
            logger.error("Failed to refresh top-%d list: %s", settings.top_n_coins, exc)
            top_symbols = []
            aborted = True

        if not aborted:
            _refresh_coins(session, top_symbols)

            device_tokens = [dt.token for dt in session.query(DeviceToken).all()]

            for symbol in _cycle_symbols(session, top_symbols):
                df = get_klines(symbol, interval="1h", limit=100)
                if df is None:
                    logger.warning("Skipping %s: klines unavailable this cycle", symbol)
                    continue

                # Informational only — a scoring bug must never block the
                # actual BUY/SELL engine below, so it gets its own guard
                # instead of sharing process_coin's exception handling.
                coin = session.query(Coin).filter_by(symbol=symbol).one_or_none()
                if coin is not None:
                    try:
                        score = compute_entry_score(df)
                        coin.entry_score = score
                        session.add(EntryScoreHistory(coin_symbol=symbol, score=score))
                    except Exception:
                        logger.exception("Failed to compute entry score for %s", symbol)

                    # A separate daily-candle fetch — the 1h klines above only
                    # cover ~4 days, nowhere near enough for a 90/180/360-day
                    # drawdown figure. Its own guard, same reasoning as the
                    # entry score: purely informational, must never cost this
                    # coin its real signal below.
                    try:
                        daily_df = get_klines(symbol, interval="1d", limit=360)
                        if daily_df is not None:
                            current_price = float(daily_df["close"].iloc[-1])
                            highs = daily_df["high"]
                            coin.pct_below_high_90d = pct_below_high(highs, current_price, 90)
                            coin.pct_below_high_180d = pct_below_high(highs, current_price, 180)
                            coin.pct_below_high_360d = pct_below_high(highs, current_price, 360)
                    except Exception:
                        logger.exception("Failed to compute drawdown stats for %s", symbol)

                try:
                    signal = process_coin(session, symbol, df)
                except Exception:
                    # Isolate this coin's failure: the rest of the cycle's
                    # signals and position updates must still be committed.
                    logger.exception("Skipping %s: processing failed this cycle", symbol)
                    if not session.is_active:
                        # A flush/transaction-level failure deactivated the
                        # transaction. Every remaining coin would now raise
                        # PendingRollbackError instead of its own real error,
                        # and the final commit is doomed anyway — stop here so
                        # the one real traceback above stays readable.
                        logger.error(
                            "Session unusable after a flush failure, "
                            "aborting the rest of this cycle (stopped at %s)",
                            symbol,
                        )
                        # Roll back explicitly so `get_session`'s closing
                        # commit() does not raise a second, misleading
                        # PendingRollbackError on top of the real error already
                        # logged above. The cycle's work is lost either way —
                        # which is exactly why nothing has been pushed yet.
                        session.rollback()
                        aborted = True
                        break
                    continue

                coins_processed += 1

                if signal is None:
                    continue

                signals_generated += 1
                # A detached, plain-data snapshot: the ORM row is expired the
                # moment this session commits and closes, and the send happens
                # after that.
                pending_notifications.append(SimpleNamespace(
                    coin_symbol=signal.coin_symbol,
                    signal_type=signal.signal_type,
                    price=signal.price,
                ))

    # Past this point the transaction has committed, so every notification
    # below refers to a signal that really is in the database.
    if not aborted:
        for snapshot in pending_notifications:
            notifications_sent += _notify_all(device_tokens, snapshot)

    logger.info(
        "Cycle complete: %d coins processed, %d signals generated, "
        "%d notifications sent",
        coins_processed,
        signals_generated,
        notifications_sent,
    )


def start_scheduler(app: FastAPI) -> None:
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_cycle, "cron", minute=1)  # 1 minute past the hour, after candle close
    scheduler.start()
    app.state.scheduler = scheduler
