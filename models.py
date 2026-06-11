from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class BitcoinTrade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_msg_id: Mapped[int] = mapped_column(BigInteger) # save entry trade and replay to entry trade when exit

    btc_amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)

    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    entry_usd_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    exit_usd_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    spent: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.0"))
    btc: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.0"))
