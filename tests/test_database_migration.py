from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from database import Base, BitcoinTrade, Company


def test_monetary_scale_migration_preserves_rows(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(config, "95c6431702c6")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO companies VALUES (1, 123.12345678, 0.123456, '2026-10-20')"
            ))
            connection.execute(text(
                "INSERT INTO trades VALUES "
                "(1, 0.123456, 12.34, 1.12345678, '2026-10-20', NULL, NULL, NULL)"
            ))

        def rows():
            with engine.connect() as connection:
                return {
                    table: connection.execute(text(f"SELECT * FROM {table}")).all()
                    for table in ("companies", "trades")
                }

        original = rows()
        command.upgrade(config, "head")
        assert rows() == original
        for table in Base.metadata.sorted_tables:
            actual = {column["name"]: column for column in inspect(engine).get_columns(table.name)}
            for column in table.columns:
                assert str(actual[column.name]["type"]) == str(column.type)
                assert actual[column.name]["nullable"] == column.nullable

        amount = Decimal("0.1234567891")
        with Session(engine) as session, session.begin():
            company = session.get(Company, 1)
            company.balance = company.btc = amount
            trade = session.get(BitcoinTrade, 1)
            trade.btc_amount = trade.entry_price = trade.entry_usd_amount = amount
            trade.exit_price = trade.exit_usd_amount = amount
            trade.exited_at = datetime.now(timezone.utc)
        with Session(engine) as session:
            company = session.get(Company, 1)
            trade = session.get(BitcoinTrade, 1)
            assert company.balance == company.btc == amount
            assert trade.btc_amount == trade.entry_price == trade.entry_usd_amount == amount
            assert trade.exit_price == trade.exit_usd_amount == amount

        command.downgrade(config, "95c6431702c6")
        for table, scales in {
            "companies": {"balance": 8, "btc": 6},
            "trades": {"btc_amount": 6, "entry_price": 2, "entry_usd_amount": 8,
                       "exit_price": 2, "exit_usd_amount": 8},
        }.items():
            for column in inspect(engine).get_columns(table):
                if column["name"] in scales:
                    assert column["type"].precision == 18
                    assert column["type"].scale == scales[column["name"]]
    finally:
        engine.dispose()
