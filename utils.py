from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from consts import INFLATION_RATE, MAX_DAILY_BUY_USD, MIN_PLATFORM_USD

if TYPE_CHECKING:
    from models import BitcoinTrade


def _to_decimal(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value))


def is_price_above_compound_interest(current_price, trade: "BitcoinTrade", exited_at: date):
    days = (exited_at - trade.entered_at.date()).days
    years = _to_decimal((days + 364) // 365)
    target_price = trade.entry_price * (1 + _to_decimal(INFLATION_RATE) / 100) ** years

    if current_price > target_price:
        pass

    return current_price > target_price


def calculate_usd_amount_from_price_range(
    lowest_price: Decimal | None,
    biggest_price: Decimal | None,
) -> Decimal:
    if lowest_price is None:
        return _to_decimal(MIN_PLATFORM_USD)

    exit_ratio = lowest_price / biggest_price
    amount_range = _to_decimal(MAX_DAILY_BUY_USD) - _to_decimal(MIN_PLATFORM_USD)

    usd_amount = _to_decimal(MAX_DAILY_BUY_USD) - amount_range * exit_ratio
    return usd_amount


def calculate_usd_amount_from_trade_counts(
    total_trades: int,
    exited_trades: int,
    company_spent: Decimal,
) -> Decimal:
    if total_trades == 0:
        return _to_decimal(MIN_PLATFORM_USD)

    exit_ratio = _to_decimal(exited_trades) / _to_decimal(total_trades)
    amount_range = _to_decimal(MAX_DAILY_BUY_USD) - _to_decimal(MIN_PLATFORM_USD)

    usd_amount = _to_decimal(MAX_DAILY_BUY_USD) - amount_range * exit_ratio

    if company_spent < 0:
        usd_amount -= company_spent/365

    if usd_amount > _to_decimal(MAX_DAILY_BUY_USD):
        return _to_decimal(MAX_DAILY_BUY_USD)

    return usd_amount
