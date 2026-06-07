from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from consts import PERCENT, DAILY_BUY_USD
from models import BitcoinTrade
from utils import _to_decimal


def update_bitcoin_trade_spread(session: Session, price: float | int | str | Decimal) -> BitcoinTrade | None:
    current_price = _to_decimal(price)
    target_price = current_price * (Decimal("1") - (_to_decimal(PERCENT) / Decimal("100")))

    trade = session.scalar(
        select(BitcoinTrade)
        .where(BitcoinTrade.price <= target_price)
        .where(BitcoinTrade.spent >= DAILY_BUY_USD)
        .where(BitcoinTrade.spread_price.is_(None))
        .order_by(BitcoinTrade.created_at.desc(), BitcoinTrade.id.desc())
    )

    if trade is None:
        return None

    trade.spread_price = current_price
    trade.spread_usd = (current_price - trade.price) * trade.btc
    trade.updated_at = datetime.now()
    session.commit()
    session.refresh(trade)

    return trade
