# backend/app/scheduler.py
"""Hourly cycle orchestration.

`run_cycle()` is the single job that ties the whole backend together:

1. Refresh the tracked coin list from the top-N ranking (upsert, never delete).
2. For each tracked coin, fetch fresh 1h candles.
3. Hand them to `process_coin`, which owns all position/signal logic.
4. Push any generated signal to every registered device token.

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

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.db import get_session
from app.market_data import get_klines, get_top_symbols
from app.models import Coin, DeviceToken
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
        else:
            session.add(Coin(
                symbol=entry["symbol"],
                name=entry["name"],
                rank=entry["rank"],
                active=True,
            ))

    current_symbols = {e["symbol"] for e in top_symbols}
    for symbol, coin in existing.items():
        if symbol not in current_symbols:
            coin.active = False

    session.flush()


def _notify_all(device_tokens: list[str], signal) -> None:
    """Push `signal` to every registered token.

    `send_signal_notification` is documented never to raise, but a failure
    there must never cost us the cycle's DB work, so it is guarded anyway.
    """
    for token in device_tokens:
        try:
            send_signal_notification(token, signal)
        except Exception:
            logger.exception(
                "Notification failed for token ending %s (%s %s)",
                token[-6:],
                signal.signal_type,
                signal.coin_symbol,
            )


def run_cycle() -> None:
    with get_session() as session:
        try:
            top_symbols = get_top_symbols()
        except Exception as exc:
            # No coin list means nothing to process — abort the cycle cleanly.
            logger.error("Failed to refresh top-30 list: %s", exc)
            return

        _refresh_coins(session, top_symbols)

        device_tokens = [dt.token for dt in session.query(DeviceToken).all()]

        for entry in top_symbols:
            symbol = entry["symbol"]
            df = get_klines(symbol, interval="1h", limit=100)
            if df is None:
                logger.warning("Skipping %s: klines unavailable this cycle", symbol)
                continue

            try:
                signal = process_coin(session, symbol, df)
            except Exception:
                # Isolate this coin's failure: the rest of the cycle's signals
                # and position updates must still be committed.
                logger.exception("Skipping %s: processing failed this cycle", symbol)
                if not session.is_active:
                    # A flush/transaction-level failure deactivated the
                    # transaction. Every remaining coin would now raise
                    # PendingRollbackError instead of its own real error, and
                    # the final commit is doomed anyway — stop here so the one
                    # real traceback above stays readable.
                    logger.error(
                        "Session unusable after a flush failure, "
                        "aborting the rest of this cycle (stopped at %s)",
                        symbol,
                    )
                    # Roll back explicitly so `get_session`'s closing commit()
                    # does not raise a second, misleading PendingRollbackError
                    # on top of the real error already logged above. The
                    # cycle's work is lost either way.
                    session.rollback()
                    return
                continue

            if signal is None:
                continue

            _notify_all(device_tokens, signal)


def start_scheduler(app: FastAPI) -> None:
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_cycle, "cron", minute=1)  # 1 minute past the hour, after candle close
    scheduler.start()
    app.state.scheduler = scheduler
