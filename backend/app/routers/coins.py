# backend/app/routers/coins.py
from fastapi import APIRouter

from app.db import get_session
from app.models import Coin, Position
from app.schemas import CoinOut

router = APIRouter(prefix="/coins", tags=["coins"])


@router.get("", response_model=list[CoinOut])
def list_coins():
    with get_session() as session:
        coins = session.query(Coin).filter_by(active=True).order_by(Coin.rank).all()
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
                ))
            else:
                result.append(CoinOut(
                    symbol=coin.symbol,
                    name=coin.name,
                    rank=coin.rank,
                    has_open_position=False,
                ))
        return result
