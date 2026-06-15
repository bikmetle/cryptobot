import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

import requests

from consts import API_KEY, PASSPHRASE, SECRET_KEY

BASE_URL = "https://api.bitget.com"
SYMBOL = "BTCUSDT"
QUOTE_PRECISION=8
QUANTITY_PRECISION=6
TIMEOUT = 10


# def _symbol_info():
#     data = _get("/api/v2/spot/public/symbols", {"symbol": SYMBOL})
#     if not data:
#         raise RuntimeError(f"Bitget returned no symbol data for {SYMBOL}")
#     return data[0]

    # symbol = _symbol_info()
    # quote_precision = int(symbol["quotePrecision"])
    # quantity_precision = int(symbol["quantityPrecision"])


@dataclass(frozen=True)
class BtcOrderResult:
    usd: Decimal
    btc: Decimal
    price: Decimal


def _to_decimal(value):
    return Decimal(str(value))


def _decimal_str(value, precision=None):
    value = _to_decimal(value)
    if precision is not None:
        step = Decimal("1").scaleb(-precision)
        value = value.quantize(step, rounding=ROUND_DOWN)
    return format(value.normalize(), "f")


def _check_response(payload):
    if payload.get("code") != "00000":
        raise RuntimeError(f"Bitget API error: {payload.get('msg', payload)}")
    return payload["data"]


def _signature(secret_key: str, timestamp, method, path, query_string="", body=""):
    message = f"{timestamp}{method}{path}"
    if query_string:
        message += f"?{query_string}"
    message += body
    digest = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode()


def _headers(method, path, query_string="", body=""):
    api_key = API_KEY
    secret_key = SECRET_KEY
    passphrase = PASSPHRASE
    if not api_key or not secret_key or not passphrase:
        raise RuntimeError("API_KEY, SECRET_KEY, and PASSPHRASE must be set")

    timestamp = str(int(time.time() * 1000))
    return {
        "ACCESS-KEY": api_key,
        "ACCESS-SIGN": _signature(secret_key, timestamp, method, path, query_string, body),
        "ACCESS-PASSPHRASE": passphrase,
        "ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json",
        "locale": "en-US",
    }


def _get(path, params=None, signed=False):
    params = params or {}
    query_string = urlencode(params)
    headers = _headers("GET", path, query_string) if signed else None
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers=headers,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return _check_response(response.json())


def _post(path, payload):
    body = json.dumps(payload, separators=(",", ":"))
    response = requests.post(
        f"{BASE_URL}{path}",
        data=body,
        headers=_headers("POST", path, body=body),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return _check_response(response.json())


def _ticker():
    data = _get("/api/v2/spot/market/tickers", {"symbol": SYMBOL})
    if not data:
        raise RuntimeError(f"Bitget returned no ticker data for {SYMBOL}")
    return data[0]


def _place_market_order(side, size):
    order = _post(
        "/api/v2/spot/trade/place-order",
        {
            "symbol": SYMBOL,
            "side": side,
            "orderType": "market",
            "size": size,
        },
    )
    return _wait_for_fill(order["orderId"])


def _wait_for_fill(order_id):
    for _ in range(10):
        data = _get(
            "/api/v2/spot/trade/orderInfo",
            {"orderId": order_id},
            signed=True,
        )
        if data and data[0]["status"] == "filled":
            return data[0]
        time.sleep(1)

    raise RuntimeError(f"Bitget order {order_id} was not filled in time")


def get_btc_prices():
    ticker = _ticker()
    buy_price = _to_decimal(ticker["askPr"] or ticker["lastPr"])
    sell_price = _to_decimal(ticker["bidPr"] or ticker["lastPr"])
    return buy_price, sell_price


def buy_btc(usd_amount):
    order = _place_market_order(
        "buy", 
        _decimal_str(usd_amount, QUOTE_PRECISION)
    )
    return BtcOrderResult(
        usd=_to_decimal(order["quoteVolume"]),
        btc=_to_decimal(order["baseVolume"]),
        price=_to_decimal(order["priceAvg"]),
    )


def sell_btc(btc_amount):
    order = _place_market_order(
        "sell",
        _decimal_str(btc_amount, QUANTITY_PRECISION),
    )
    return BtcOrderResult(
        usd=_to_decimal(order["quoteVolume"]),
        btc=_to_decimal(order["baseVolume"]),
        price=_to_decimal(order["priceAvg"]),
    )
