from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from consts import INFLATION, INTEREST, DAILY_BUY_USD, DAILY_BUY_USD, MIN_PLATFORM_USD
from converters import _to_decimal

if TYPE_CHECKING:
    from models import Company
    from models import BitcoinTrade


def is_price_above_compound_interest(current_price, trade: "BitcoinTrade", exited_at: date):
    # TODO exited_at = date.now()
    days = (exited_at - trade.entered_at.date()).days
    years = (days + 364) // 365
    target_price = trade.entry_price * (1 + INTEREST / 100) ** years

    return current_price > target_price


def is_usd_delta_above_min_platform_usd(entry_usd: Decimal, exit_price: Decimal, trade: "BitcoinTrade"):
    exit_usd = exit_price*trade.btc_amount
    usd_delta = entry_usd - exit_usd

    return abs(usd_delta) > MIN_PLATFORM_USD


def calculate_usd_amount(
    company: "Company",
    current_date: date
) -> Decimal:
    days = (current_date - company.created_at.date()).days
    years = _to_decimal(days/365)
    usd_amount = DAILY_BUY_USD * (1 + INFLATION / 100) ** years

    return usd_amount


def _to_decimal(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value))
