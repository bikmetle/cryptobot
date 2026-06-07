from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from consts import DAILY_BUY_USD
from db_helpers import mark_bitcoin_trade_bought_back, update_bitcoin_trade_spread
from models import Base, BitcoinTrade


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        yield session


def test_update_bitcoin_trade_spread_updates_trade_below_five_percent(session):
    trade = BitcoinTrade(
        price=Decimal("95.00"),
        btc=Decimal("0.10000000"),
        spent=Decimal(DAILY_BUY_USD),
        created_at=datetime(2026, 6, 7),
    )
    session.add(trade)
    session.commit()

    updated_trade = update_bitcoin_trade_spread(session, Decimal("100.00"))

    assert updated_trade is trade
    assert updated_trade.spread_price == Decimal("100.00")
    assert updated_trade.spread_usd == Decimal("0.50000000")
    assert updated_trade.updated_at is not None


def test_update_bitcoin_trade_spread_returns_none_when_no_trade_is_low_enough(session):
    trade = BitcoinTrade(
        price=Decimal("96.00"),
        btc=Decimal("0.10000000"),
        spent=Decimal(DAILY_BUY_USD),
        created_at=datetime(2026, 6, 7),
    )
    session.add(trade)
    session.commit()

    updated_trade = update_bitcoin_trade_spread(session, Decimal("100.00"))

    assert updated_trade is None
    assert trade.spread_price is None
    assert trade.spread_usd is None


def test_update_bitcoin_trade_spread_skips_already_updated_trade(session):
    trade = BitcoinTrade(
        price=Decimal("95.00"),
        btc=Decimal("0.10000000"),
        spent=Decimal(DAILY_BUY_USD),
        spread_price=Decimal("99.00"),
        spread_usd=Decimal("0.40"),
        created_at=datetime(2026, 6, 7),
    )
    session.add(trade)
    session.commit()

    updated_trade = update_bitcoin_trade_spread(session, Decimal("100.00"))

    assert updated_trade is None
    assert trade.spread_price == Decimal("99.00")
    assert trade.spread_usd == Decimal("0.40")


def test_mark_bitcoin_trade_bought_back_updates_trade_with_spread_price_and_higher_price(session):
    trade = BitcoinTrade(
        price=Decimal("105.00"),
        btc=Decimal("0.10000000"),
        spent=Decimal(DAILY_BUY_USD),
        spread_price=Decimal("100.00"),
        created_at=datetime(2026, 6, 7),
    )
    session.add(trade)
    session.commit()

    updated_trade = mark_bitcoin_trade_bought_back(session, Decimal("100.00"))

    assert updated_trade is trade
    assert updated_trade.is_bought_back is True


def test_mark_bitcoin_trade_bought_back_requires_spread_price(session):
    trade = BitcoinTrade(
        price=Decimal("105.00"),
        btc=Decimal("0.10000000"),
        spent=Decimal(DAILY_BUY_USD),
        created_at=datetime(2026, 6, 7),
    )
    session.add(trade)
    session.commit()

    updated_trade = mark_bitcoin_trade_bought_back(session, Decimal("100.00"))

    assert updated_trade is None
    assert trade.is_bought_back is False


def test_mark_bitcoin_trade_bought_back_requires_trade_price_above_given_price(session):
    trade = BitcoinTrade(
        price=Decimal("100.00"),
        btc=Decimal("0.10000000"),
        spent=Decimal(DAILY_BUY_USD),
        spread_price=Decimal("99.00"),
        created_at=datetime(2026, 6, 7),
    )
    session.add(trade)
    session.commit()

    updated_trade = mark_bitcoin_trade_bought_back(session, Decimal("100.00"))

    assert updated_trade is None
    assert trade.is_bought_back is False
