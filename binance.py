"""Binance BTC/USDT spot orders using HMAC API credentials."""

import hashlib
import hmac
import time
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

import requests

from consts import BINANCE_API_KEY, BINANCE_SECRET_KEY, ENV, Environment
from exchange_types import BtcOrderResult
from trading_exceptions import LessThanMinimumAmountException

BASE_URL = "https://api.binance.com"
SYMBOL = "BTCUSDT"
TIMEOUT = 10
MAX_RETRIES = 10


def _response_data(response):
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        response.raise_for_status()
        raise RuntimeError("Binance returned an invalid JSON response")

    if isinstance(payload, dict) and payload.get("code", 0) < 0:
        message = str(payload.get("msg", payload))
        detail = f"Binance API error {payload['code']}: {message}"
        if payload["code"] == -1013 and "MIN_NOTIONAL" in message:
            raise LessThanMinimumAmountException(detail)
        if payload["code"] == -1013 and "NOTIONAL" in message:
            # NOTIONAL can reject either the minimum or maximum value.
            # Neither case executed an order, so the strategy can skip it.
            raise LessThanMinimumAmountException(detail)
        raise RuntimeError(detail)
    response.raise_for_status()
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected Binance API response: {payload}")
    return payload


def _request(method, path, params=None, signed=False):
    if ENV != Environment.PROD:
        raise RuntimeError("The real Binance client requires ENV=PROD")
    params = dict(params or {})
    headers = {}
    if signed:
        if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
            raise RuntimeError("BINANCE_API_KEY and BINANCE_SECRET_KEY must be set")
        params.update(timestamp=int(time.time() * 1000), recvWindow=5000)
        query = urlencode(params)
        params["signature"] = hmac.new(
            BINANCE_SECRET_KEY.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        headers["X-MBX-APIKEY"] = BINANCE_API_KEY
    response = requests.request(
        method, f"{BASE_URL}{path}", params=params, headers=headers, timeout=TIMEOUT
    )
    return _response_data(response)


def _symbol_info():
    data = _request("GET", "/api/v3/exchangeInfo", {"symbol": SYMBOL})
    symbols = data.get("symbols", [])
    if not symbols or symbols[0]["status"] != "TRADING":
        raise RuntimeError(f"Binance {SYMBOL} is not available for trading")
    return symbols[0]


def _decimal_str(value):
    return format(value.normalize(), "f")


def _place_market_order(side, size_name, size):
    order = _request(
        "POST", "/api/v3/order",
        {"symbol": SYMBOL, "side": side, "type": "MARKET",
         size_name: size, "newOrderRespType": "FULL"},
        signed=True,
    )
    for attempt in range(MAX_RETRIES):
        status = order["status"]
        if status == "FILLED":
            btc = Decimal(order["executedQty"])
            usd = Decimal(order["cummulativeQuoteQty"])
            if btc <= 0 or usd <= 0:
                raise RuntimeError(f"Binance order {order['orderId']} has invalid fill amounts")
            return BtcOrderResult(usd=usd, btc=btc, price=usd / btc)
        if status in {"CANCELED", "REJECTED", "EXPIRED", "EXPIRED_IN_MATCH"}:
            raise RuntimeError(f"Binance order {order['orderId']} ended with {status}")
        time.sleep(1)
        order = _request(
            "GET", "/api/v3/order",
            {"symbol": SYMBOL, "orderId": order["orderId"]}, signed=True,
        )
    raise RuntimeError(f"Binance order {order['orderId']} was not filled in time")


def get_btc_prices():
    ticker = _request("GET", "/api/v3/ticker/bookTicker", {"symbol": SYMBOL})
    return Decimal(ticker["askPrice"]), Decimal(ticker["bidPrice"])


def buy_btc(usd_amount):
    info = _symbol_info()
    precision = int(info["quoteAssetPrecision"])
    amount = Decimal(str(usd_amount)).quantize(
        Decimal(1).scaleb(-precision), rounding=ROUND_DOWN
    )
    if amount <= 0:
        raise LessThanMinimumAmountException("Binance buy amount rounds down to zero")
    return _place_market_order("BUY", "quoteOrderQty", _decimal_str(amount))


def sell_btc(btc_amount):
    info = _symbol_info()
    filters = [f for f in info["filters"] if f["filterType"] in {"LOT_SIZE", "MARKET_LOT_SIZE"}]
    amount = Decimal(str(btc_amount))
    for rule in filters:
        step = Decimal(rule["stepSize"])
        if step > 0:
            amount = (amount / step).to_integral_value(rounding=ROUND_DOWN) * step
    if amount <= 0 or any(amount < Decimal(f["minQty"]) for f in filters):
        raise LessThanMinimumAmountException("Binance sell amount is below minimum quantity")
    for rule in filters:
        step = Decimal(rule["stepSize"])
        if step > 0 and amount % step:
            raise RuntimeError("Binance quantity does not satisfy lot size filters")
    return _place_market_order("SELL", "quantity", _decimal_str(amount))
