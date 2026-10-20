from decimal import Decimal
import logging

from consts import ENV, EXCHANGE, Environment, Exchange
from db_helpers import record_trade_entry
from db_helpers import record_trade_exit
from db_helpers import get_company, get_trades_to_exit, update_company
from trading_exceptions import ExitFailedException, LessThanMinimumAmountException
from utils import calculate_usd_amount

if ENV == Environment.PROD:
    if EXCHANGE == Exchange.BYBIT:
        from bybit import buy_btc, get_btc_prices, sell_btc
    elif EXCHANGE == Exchange.BINANCE:
        from binance import buy_btc, get_btc_prices, sell_btc
    elif EXCHANGE == Exchange.BITGET:
        from bitget import buy_btc, get_btc_prices, sell_btc
    else:
        raise NotImplemented()
else:
    from bitget_mock import buy_btc, get_btc_prices, sell_btc

logger = logging.getLogger(__name__)


def exit_order(sell_price, planned_entry_usd, session, traded_at):
    trades = get_trades_to_exit(session, sell_price, planned_entry_usd, traded_at)
    for trade in trades:
        try:
            order = sell_btc(trade.btc_amount)
        except LessThanMinimumAmountException as exc:
            logger.warning("Skipping trade_id %s: %s", trade.id, exc)
            continue

        # TODO from order.btc
        # compare order.btc trade.btc
        closed_trade_btc = trade.btc_amount
        # TODO from order.usdt
        closed_trade_usd = order.price * closed_trade_btc
        record_trade_exit(trade, closed_trade_usd, order.price, traded_at)
        update_company(session, closed_trade_usd, -closed_trade_btc)
        return order.btc, order.usd

    raise ExitFailedException()


def entry_order(planned_entry_usd, session, traded_at):
    order = buy_btc(planned_entry_usd)
    entry_btc = order.btc
    entry_usd = order.usd
    order_price = order.price

    record_trade_entry(session, entry_btc, entry_usd, order_price, traded_at)
    company = update_company(session, -entry_usd, entry_btc)

    return company, entry_btc, entry_usd

def trade(session, traded_at):
    """Execute a trade using a session with no active transaction."""
    with session.begin():
        company = get_company(session)
        planned_entry_usd = calculate_usd_amount(company, traded_at)
        buy_price, sell_price = get_btc_prices()
        planned_entry_btc = planned_entry_usd / buy_price

        try:
            exit_btc, exit_usd = exit_order(sell_price, planned_entry_btc, session, traded_at)
        except ExitFailedException:
            exit_btc = exit_usd = 0

        company, entry_btc, entry_usd = entry_order(planned_entry_usd, session, traded_at)

        if exit_btc == 0:
            message = (
                f"\nbought {entry_btc:,.6f} BTC"
                f"\nspent ${entry_usd:,.8f}"
            )

        else:
            message = (
                f"\nsold {exit_btc - entry_btc:,.6f} BTC"
                f"\nspent ${entry_usd-exit_usd:,.8f}"
            )

        current_btc_value = company.btc * sell_price
        message += (
            f"\n\nBalance: ${company.balance:,.2f}"
            f"\nBTC price: ${sell_price:,.2f}"
            f"\nOwned: {company.btc:.6f} BTC"
            f"\nValue: ${current_btc_value:,.2f}"
            f"\nProfit/Loss: ${current_btc_value + company.balance:,.2f}"
        )

        return message
