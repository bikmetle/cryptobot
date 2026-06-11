from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db_helpers import get_trades_count
from models import Base, BitcoinTrade


def test_get_trades_count_returns_total_and_exited_trades_for_last_40_days():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        session.add_all([
            BitcoinTrade(
                btc_amount=Decimal("0.1"),
                entry_price=Decimal("90.00"),
                entry_usd_amount=Decimal("5.00"),
                entered_at=datetime(2026, 4, 1),
                exit_price=Decimal("120.00"),
                exit_usd_amount=Decimal("6.00"),
                exited_at=datetime(2026, 4, 10),
            ),
            BitcoinTrade(
                btc_amount=Decimal("0.1"),
                entry_price=Decimal("100.00"),
                entry_usd_amount=Decimal("5.00"),
                entered_at=datetime(2026, 5, 20),
            ),
            BitcoinTrade(
                btc_amount=Decimal("0.1"),
                entry_price=Decimal("110.00"),
                entry_usd_amount=Decimal("5.00"),
                entered_at=datetime(2026, 5, 21),
                exit_price=Decimal("120.00"),
                exit_usd_amount=Decimal("6.00"),
                exited_at=datetime(2026, 6, 10),
            ),
        ])
        session.commit()

        total_trades, exited_trades = get_trades_count(session, datetime(2026, 6, 10))

    assert total_trades == 2
    assert exited_trades == 1


def test_get_trades_count_returns_zeroes_when_no_trades_exist():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        total_trades, exited_trades = get_trades_count(session, datetime(2026, 6, 10))

    assert total_trades == 0
    assert exited_trades == 0
