from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class BitcoinTrade(Base):
    __tablename__ = "bitcoin_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    btc: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    spent: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    spread_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    spread_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    updated_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    is_bought_back: Mapped[bool] = mapped_column(Boolean, default=False)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    spent: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0.0))
    btc: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal(0.0))
