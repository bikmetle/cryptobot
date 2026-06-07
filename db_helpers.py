from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from consts import PERCENT, DAILY_BUY_USD
from models import BitcoinTrade, Company
from utils import _to_decimal


def add_bitcoin_trade(
    session: Session,
    price: float | int | str | Decimal,
    usd: float | int | str | Decimal,
) -> BitcoinTrade:
    trade_price = _to_decimal(price)
    spent = _to_decimal(usd)
    trade = BitcoinTrade(
        price=trade_price,
        btc=spent / trade_price,
        spent=spent,
    )

    session.add(trade)
    session.commit()
    session.refresh(trade)

    return trade


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


def mark_bitcoin_trade_bought_back(session: Session, price: float | int | str | Decimal) -> BitcoinTrade | None:
    current_price = _to_decimal(price)

    trade = session.scalar(
        select(BitcoinTrade)
        .where(BitcoinTrade.spread_price.is_not(None))
        .where(BitcoinTrade.price > current_price)
        .where(BitcoinTrade.is_bought_back.is_(False))
        .order_by(BitcoinTrade.created_at.desc(), BitcoinTrade.id.desc())
    )

    if trade is None:
        return None

    trade.is_bought_back = True
    session.commit()
    session.refresh(trade)

    return trade


def update_company(session: Session, spent: float | int | str | Decimal, btc: float | int | str | Decimal, id: int) -> Company:
    company = session.scalar(
        select(Company)
        .where(Company.id == id)
    )

    if company is None:
        raise ValueError("Company not found")

    company.spent += _to_decimal(spent)
    company.btc += _to_decimal(btc)
    session.commit()
    session.refresh(company)

    return company
