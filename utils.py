from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from consts import INTEREST, MAX_DAILY_BUY_USD, MIN_DAILY_BUY_USD, MIN_PLATFORM_USD
from models import Company, TradeKind
from converters import _to_decimal

if TYPE_CHECKING:
    from models import BitcoinTrade


def is_price_above_compound_interest(current_price, trade: "BitcoinTrade", exited_at: date):
    # TODO exited_at = date.now()
    days = (exited_at - trade.entered_at.date()).days
    years = (days + 364) // 365
    target_price = trade.entry_price * (1 + INTEREST / 100) ** years

    return current_price > target_price


def calculate_usd_amount(
    total_trades: int,
    exited_trades: int,
    company: Company,
    trade_kind: TradeKind
) -> Decimal:
    if total_trades < 90:
        return MAX_DAILY_BUY_USD//3

    exit_ratio = _to_decimal(exited_trades/total_trades)
    amount_range = MAX_DAILY_BUY_USD - MIN_PLATFORM_USD

    usd_amount = MAX_DAILY_BUY_USD - amount_range * exit_ratio

    if trade_kind == TradeKind.EXIT and company.spent < 0:
        usd_amount -= company.spent/100

    if usd_amount > MAX_DAILY_BUY_USD:
        return MAX_DAILY_BUY_USD

    if usd_amount < MIN_DAILY_BUY_USD:
        return MIN_DAILY_BUY_USD

    return usd_amount
