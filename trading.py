import logging

from bitget import buy_btc, get_btc_prices, sell_btc
# if env==test:
# from bitget_mock import buy_btc, get_btc_prices, sell_btc
from db_helpers import record_trade_entry
from db_helpers import record_trade_exit
from db_helpers import get_company, get_trades_to_exit, update_company
from trading_exceptions import ExitFailedException, LessThanMinimumAmountException
from utils import calculate_usd_amount


logger = logging.getLogger(__name__)

def try_to_exit(sell_price, planned_entry_usd, planned_entry_btc, session, traded_at):
    trades_to_exit = get_trades_to_exit(session, sell_price, planned_entry_usd, traded_at)
    for trade_to_exit in trades_to_exit:
        exiting_trade_usd = sell_price * trade_to_exit.btc_amount
        exiting_trade_btc = trade_to_exit.btc_amount
        usd_needed_for_entry = planned_entry_usd - exiting_trade_usd

        try:
            if usd_needed_for_entry > 0:
                order = buy_btc(usd_needed_for_entry)
            else:
                order = sell_btc(exiting_trade_btc - planned_entry_btc)
        except LessThanMinimumAmountException as exc:
            logger.warning("Skipping trade_id %s: %s", trade_to_exit.id, exc)
            continue

        if usd_needed_for_entry > 0:
            entry_btc = exiting_trade_btc + order.btc
            entry_usd = exiting_trade_usd + order.usd
            message = (
                f"\nbought {order.btc:,.6f} BTC"
                f"\nspent ${order.usd:,.8f}"
            )
        else:
            entry_btc = exiting_trade_btc - order.btc
            entry_usd = exiting_trade_usd - order.usd
            message = (
                f"\nsold {order.btc:,.6f} BTC"
                f"\nearned ${order.usd:,.8f}"
            )

        order_price = order.price
        closed_trade_usd = order_price * trade_to_exit.btc_amount
        record_trade_exit(session, trade_to_exit, closed_trade_usd, order_price, traded_at)
        update_company(session, closed_trade_usd, -trade_to_exit.btc_amount)
        return order_price, entry_btc, entry_usd, message

    raise ExitFailedException()


def trade(session, traded_at):
    """Execute a trade using a session with no active transaction."""
    with session.begin():
        company = get_company(session)
        planned_entry_usd = calculate_usd_amount(company, traded_at)
        buy_price, sell_price = get_btc_prices()
        planned_entry_btc = planned_entry_usd / buy_price

        try:
            order_price, entry_btc, entry_usd, message = try_to_exit(sell_price, planned_entry_usd, planned_entry_btc, session, traded_at)

        except ExitFailedException:
            order = buy_btc(planned_entry_usd)
            entry_btc = order.btc
            entry_usd = order.usd
            order_price = order.price

            message = (
                f"\nbought {entry_btc:,.6f} BTC"
                f"\nspent ${entry_usd:,.8f}"
            )

        record_trade_entry(session, entry_btc, entry_usd, order_price, traded_at)
        company = update_company(session, -entry_usd, entry_btc)

        current_btc_value = company.btc * sell_price
        message += (
            f"\n\nBalance: ${company.balance:,.2f}"
            f"\nBTC price: ${sell_price:,.2f}"
            f"\nOwned: {company.btc:.6f} BTC"
            f"\nValue: ${current_btc_value:,.2f}"
            f"\nProfit/Loss: ${current_btc_value + company.balance:,.2f}"
        )

        return message
