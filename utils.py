from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from consts import INFLATION, INTEREST, DAILY_BUY_USD, MIN_PLATFORM_USD

if TYPE_CHECKING:
    from database import Company
    from database import BitcoinTrade


def _to_decimal(value: float | int | str | Decimal | None) -> Decimal:
    if value is None:
        raise RuntimeError("value is not set")
    return Decimal(str(value))


def is_price_above_compound_interest(sell_price, trade: "BitcoinTrade", traded_at: date):
    days = (traded_at - trade.entered_at.date()).days
    years = (days + 364) // 365
    target_price = trade.entry_price * (1 + _to_decimal(INTEREST) / 100) ** years

    return sell_price > target_price


def is_usd_delta_above_min_platform_usd(planned_entry_usd: Decimal, sell_price: Decimal, trade: "BitcoinTrade"):
    exit_usd = sell_price*trade.btc_amount
    usd_delta = planned_entry_usd - exit_usd

    return abs(usd_delta) > _to_decimal(MIN_PLATFORM_USD)


def calculate_usd_amount(
    company: "Company",
    current_date: date
) -> Decimal:
    days = (current_date - company.created_at.date()).days
    years = _to_decimal(days/365)
    usd_amount = _to_decimal(DAILY_BUY_USD) * (1 + _to_decimal(INFLATION) / 100) ** years

    return usd_amount
