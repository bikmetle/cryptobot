from datetime import datetime, timezone
from bitget import buy_btc, get_btc_prices, sell_btc
from db_helpers import enter, exit, get_company, get_trade_to_exit, update_company
from utils import calculate_usd_amount


def trade(session):
    msg = ""
    date = datetime.now(timezone.utc)
    company = get_company(session)
    entry_usd = calculate_usd_amount(company, date)
    entry_price, exit_price = get_btc_prices()
    entry_btc = entry_usd/entry_price
    trade_to_exit = get_trade_to_exit(session, exit_price, entry_usd, date)

    if trade_to_exit:
        exit_usd = exit_price*trade_to_exit.btc_amount
        exit_btc = trade_to_exit.btc_amount

        usd_delta = entry_usd - exit_usd
        btc_delta = entry_btc - exit_btc

        if usd_delta > 0:
            result = buy_btc(usd_delta)
            btc = exit_btc+result.btc
            usd = exit_usd+result.usd

            msg += (
                f"\nbought {result.btc:,.6f} BTC"
                f"\nspent ${result.usd:,.8f}"
            )
            
        elif usd_delta < 0:
            result = sell_btc(btc_delta)
            btc = exit_btc-result.btc
            usd = exit_usd-result.usd

            msg += (
                f"\nsold {result.btc:,.6f} BTC"
                f"\nearned ${result.usd:,.8f}"
            )

        else:
            raise RuntimeError("Trade exit selected with zero USD delta")

        price = result.price

        exit(session, trade_to_exit, usd, price, date)
        company = update_company(session, usd, -btc)

    else:
        result = buy_btc(entry_usd)
        btc = result.btc
        usd = result.usd
        price = result.price

        msg += (
            f"\nbought {btc:,.6f} BTC"
            f"\nspent ${usd:,.8f}"
        )

    enter(session, btc, usd, price, date)
    company = update_company(session, -usd, btc)

    current_value = company.btc * exit_price
    msg += (
        f"\n\nBalance: ${company.balance:,.2f}"
        f"\nBTC price: ${exit_price:,.2f}"
        f"\nOwned: {company.btc:.8f} BTC"
        f"\nValue: ${current_value:,.2f}"
        f"\nProfit/Loss: ${current_value + company.balance:,.2f}"
    )

    return msg
