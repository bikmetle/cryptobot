from datetime import datetime
from decimal import Decimal
import os
from sqlalchemy import DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cryptobot.db")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class BitcoinTrade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)

    btc_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    entry_usd_amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    exit_usd_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.0"))
    btc: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
