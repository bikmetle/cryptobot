from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from consts import PERCENT, DAILY_BUY_USD, MIN_PLATFORM_USD
from models import BitcoinTrade, Company
from utils import _to_decimal


def enter(
    session: Session,
    price: float | int | str | Decimal,
) -> BitcoinTrade:
    price=_to_decimal(price)
    usd = _to_decimal(DAILY_BUY_USD)
    btc=usd/price

    trade = BitcoinTrade(
        btc_amount=btc,
        entry_price=price,
        entry_usd_amount=usd,
        entered_at=datetime.now()
    )

    session.add(trade)
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


def exit(session: Session, price: float | int | str | Decimal) -> BitcoinTrade | None:
    price=_to_decimal(price)
    target_price = price * (Decimal("1") - (_to_decimal(PERCENT) / Decimal("100")))

    trade = session.scalar(
        select(BitcoinTrade)
        .where(BitcoinTrade.entry_price <= target_price)
        .where(BitcoinTrade.exit_price.is_(None))
        .order_by(BitcoinTrade.entered_at.desc(), BitcoinTrade.id.desc())
    )

    if trade is None:
        return None

    usd = trade.btc_amount*price

    trade.exit_price=price
    trade.exit_usd_amount=usd
    trade.exited_at=datetime.now()

    session.commit()
    session.refresh(trade)

    return trade
