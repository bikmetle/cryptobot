from converters import _to_decimal


current_price = _to_decimal(0)

entry_usd = _to_decimal(0)
entry_btc = _to_decimal(0)

exit_usd = _to_decimal(0)
exit_btc = _to_decimal(0)


def get_btc_price():
    pass


def buy_btc(usd_amount):
    return entry_usd, entry_btc, current_price


def sell_btc(usd_amount):
    return exit_usd, exit_btc, current_price
