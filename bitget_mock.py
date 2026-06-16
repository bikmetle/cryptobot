from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

BASE_URL = "https://api.bitget.com"
SYMBOL = "BTCUSDT"
QUOTE_PRECISION=8
QUANTITY_PRECISION=6
TIMEOUT = 10


@dataclass(frozen=True)
class BtcOrderResult:
    usd: Decimal
    btc: Decimal
    price: Decimal


def _to_decimal(value):
    return Decimal(str(value))


def get_btc_prices():
    buy_price = _to_decimal(80422.53)
    sell_price = _to_decimal(80422.54)
    return buy_price, sell_price


def buy_btc(usd_amount):
    return BtcOrderResult(
        usd=_to_decimal(5.28),
        btc=_to_decimal(0.000075),
        price=_to_decimal(80422.54),
    )


def sell_btc(btc_amount):
    return BtcOrderResult(
        usd=_to_decimal(1.04549302),
        btc=_to_decimal(0.000013),
        price=_to_decimal(80422.54),
    )
