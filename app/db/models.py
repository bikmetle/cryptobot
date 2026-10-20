from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BitcoinTrade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)

    btc_amount: Mapped[Decimal] = mapped_column(Numeric(22, 10), nullable=False)

    entry_price: Mapped[Decimal] = mapped_column(Numeric(26, 10), nullable=False)
    entry_usd_amount: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(26, 10), nullable=True)
    exit_usd_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=Decimal("0.0"))
    btc: Mapped[Decimal] = mapped_column(Numeric(22, 10), default=Decimal("0.0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
