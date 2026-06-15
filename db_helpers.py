from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import BitcoinTrade, Company
from utils import is_price_above_compound_interest, is_usd_delta_above_min_platform_usd


def enter(
    session: Session,
    btc: Decimal,
    usd: Decimal,
    price: Decimal,
    entered_at: datetime,
) -> BitcoinTrade:
    trade = BitcoinTrade(
        btc_amount=btc,
        entry_usd_amount=usd,
        entry_price=price,
        entered_at=entered_at,
    )

    session.add(trade)
    session.commit()
    session.refresh(trade)

    return trade


def update_company(session: Session, usd_amount: Decimal, btc: Decimal) -> Company:
    company = session.scalar(
        select(Company)
    )

    if company is None:
        raise ValueError("Company not found")

    company.balance += usd_amount
    company.btc += btc
    session.commit()
    session.refresh(company)

    return company


def exit(session: Session, trade: BitcoinTrade,  usd: Decimal, price: Decimal, exited_at: datetime) -> BitcoinTrade:
    trade.exit_usd_amount=usd
    trade.exit_price=price
    trade.exited_at=exited_at

    session.commit()
    session.refresh(trade)

    return trade


def get_company(session: Session) -> Company:
    company = session.scalar(
        select(Company)
    )

    if company is None:
        company = Company(
            created_at = datetime.now()
        )

        session.add(company)
        session.commit()

    return company


def get_trade_to_exit(session: Session, price: Decimal, entry_usd: Decimal, exited_at: datetime) -> BitcoinTrade | None:
    trades = session.scalars(
        select(BitcoinTrade)
        .where(BitcoinTrade.entry_price <= price)
        .where(BitcoinTrade.exit_price.is_(None))
        .order_by(BitcoinTrade.entered_at.asc(), BitcoinTrade.id.asc())
    ).all()

    for trade in trades:
        if not is_price_above_compound_interest(price, trade, exited_at):
            continue

        if not is_usd_delta_above_min_platform_usd(entry_usd, price, trade):
            continue

        return trade
    
    return None
