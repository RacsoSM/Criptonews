# backend/app/routers/coins.py
from fastapi import APIRouter
from sqlalchemy import or_

from app.db import get_session
from app.market_data import get_current_prices
from app.models import Coin, Position
from app.schemas import CoinOut

router = APIRouter(prefix="/coins", tags=["coins"])


@router.get("", response_model=list[CoinOut])
def list_coins():
    with get_session() as session:
        # Inactive coins (dropped out of the top-N ranking) are still listed
        # while they hold an OPEN position: the user must be able to see — and
        # eventually exit — a position the scheduler is still monitoring.
        open_symbols = {
            symbol
            for (symbol,) in session.query(Position.coin_symbol)
            .filter_by(status="OPEN")
            .distinct()
            .all()
        }
        coins = (
            session.query(Coin)
            .filter(or_(Coin.active.is_(True), Coin.symbol.in_(open_symbols)))
            .order_by(Coin.rank)
            .all()
        )
        # One batched Binance call for every listed coin's current price,
        # instead of the Android client fetching each coin's candles just to
        # read the latest close. Never lets a price-fetch failure break the
        # listing: get_current_prices returns {} on any error, so every coin
        # just falls back to a null current_price for this request.
        current_prices = get_current_prices([coin.symbol for coin in coins])
        result = []
        for coin in coins:
            position = (
                session.query(Position)
                .filter_by(coin_symbol=coin.symbol, status="OPEN")
                .one_or_none()
            )
            if position is not None:
                result.append(CoinOut(
                    symbol=coin.symbol,
                    name=coin.name,
                    rank=coin.rank,
                    has_open_position=True,
                    entry_price=position.entry_price,
                    stop_loss=position.stop_loss,
                    take_profit=position.take_profit,
                    image_url=coin.image_url,
                    current_price=current_prices.get(coin.symbol),
                ))
            else:
                result.append(CoinOut(
                    symbol=coin.symbol,
                    name=coin.name,
                    rank=coin.rank,
                    has_open_position=False,
                    image_url=coin.image_url,
                    current_price=current_prices.get(coin.symbol),
                ))
        return result
