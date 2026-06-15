from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import BitcoinTrade, Company
from utils import is_price_above_compound_interest, is_usd_delta_above_min_platform_usd


def enter(
    session: Session,
    entry_btc: Decimal,
    entry_usd: Decimal,
    order_price: Decimal,
    traded_at: datetime,
) -> BitcoinTrade:
    trade = BitcoinTrade(
        btc_amount=entry_btc,
        entry_usd_amount=entry_usd,
        entry_price=order_price,
        entered_at=traded_at,
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


def exit(session: Session, trade: BitcoinTrade, closed_trade_usd:Decimal, order_price: Decimal, exited_at: datetime) -> BitcoinTrade:
    trade.exit_usd_amount=closed_trade_usd
    trade.exit_price=order_price
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

def get_trade_to_exit(session: Session, sell_price: Decimal, planned_entry_usd: Decimal, traded_at: datetime) -> BitcoinTrade | None:
    trades = session.scalars(
        select(BitcoinTrade)
        .where(BitcoinTrade.entry_price <= sell_price)
        .where(BitcoinTrade.exit_price.is_(None))
        .order_by(BitcoinTrade.entered_at.asc(), BitcoinTrade.id.asc())
    ).all()

    for trade in trades:
        if not is_price_above_compound_interest(sell_price, trade, traded_at):
            continue

        if not is_usd_delta_above_min_platform_usd(planned_entry_usd, sell_price, trade):
            continue

        return trade
    
    return None
