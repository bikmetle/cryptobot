"""Bybit V5 BTC/USDT spot orders using HMAC API credentials."""

import hashlib
import hmac
import json
import time
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

import requests

from consts import BYBIT_API_KEY, BYBIT_BASE_URL, BYBIT_SECRET_KEY, ENV, Environment
from exchange_types import BtcOrderResult
from trading_exceptions import LessThanMinimumAmountException

BASE_URL = BYBIT_BASE_URL
SYMBOL = "BTCUSDT"
TIMEOUT = 10
MAX_RETRIES = 10
RECV_WINDOW = "5000"


def _response_data(response):
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        response.raise_for_status()
        raise RuntimeError("Bybit returned an invalid JSON response")
    response.raise_for_status()
    if not isinstance(payload, dict) or "retCode" not in payload:
        raise RuntimeError(f"Unexpected Bybit API response: {payload}")
    if payload["retCode"] != 0:
        detail = f"Bybit API error {payload['retCode']}: {payload.get('retMsg', '')}"
        if payload["retCode"] in {170136, 170140}:
            raise LessThanMinimumAmountException(detail)
        raise RuntimeError(detail)
    if not isinstance(payload.get("result"), dict):
        raise RuntimeError(f"Unexpected Bybit API response: {payload}")
    return payload["result"]


def _request(method, path, params=None, signed=False):
    if ENV != Environment.PROD:
        raise RuntimeError("The real Bybit client requires ENV=PROD")
    params = dict(params or {})
    # Send the exact query/body used to compute the signature.
    encoded = urlencode(params) if method == "GET" else json.dumps(params, separators=(",", ":"))
    headers = {}
    if signed:
        if not BYBIT_API_KEY or not BYBIT_SECRET_KEY:
            raise RuntimeError("BYBIT_API_KEY and BYBIT_SECRET_KEY must be set")
        timestamp = str(int(time.time() * 1000))
        signature = hmac.new(
            BYBIT_SECRET_KEY.encode(),
            f"{timestamp}{BYBIT_API_KEY}{RECV_WINDOW}{encoded}".encode(),
            hashlib.sha256,
        ).hexdigest()
        headers.update({
            "X-BAPI-API-KEY": BYBIT_API_KEY,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": RECV_WINDOW,
            "X-BAPI-SIGN": signature,
        })
    kwargs = {"params": encoded} if method == "GET" else {"data": encoded}
    if method != "GET":
        headers["Content-Type"] = "application/json"
    response = requests.request(
        method, f"{BASE_URL}{path}", headers=headers, timeout=TIMEOUT, **kwargs
    )
    return _response_data(response)


def _symbol_info():
    result = _request("GET", "/v5/market/instruments-info", {"category": "spot", "symbol": SYMBOL})
    for symbol in result.get("list", []):
        if symbol["symbol"] == SYMBOL and symbol["status"] == "Trading":
            return symbol
    raise RuntimeError(f"Bybit {SYMBOL} is not available for trading")


def _rounded_amount(value, precision):
    amount = Decimal(str(value))
    step = Decimal(precision)
    if not amount.is_finite() or not step.is_finite() or step <= 0:
        raise ValueError("Bybit amount and precision must be finite with positive precision")
    amount = (amount / step).to_integral_value(rounding=ROUND_DOWN) * step
    if amount <= 0:
        raise LessThanMinimumAmountException("Bybit order amount rounds down to zero")
    return amount


def _place_market_order(side, unit, amount):
    result = _request("POST", "/v5/order/create", {
        "category": "spot", "symbol": SYMBOL, "side": side,
        "orderType": "Market", "qty": format(amount.normalize(), "f"),
        "marketUnit": unit, "isLeverage": 0,
    }, signed=True)
    order_id = result["orderId"]
    # One initial lookup, then at most MAX_RETRIES further lookups. Never resubmit.
    for attempt in range(MAX_RETRIES + 1):
        orders = _request("GET", "/v5/order/realtime", {
            "category": "spot", "symbol": SYMBOL, "orderId": order_id,
        }, signed=True)
        for order in orders.get("list", []):
            if order["orderId"] != order_id:
                continue
            status = order["orderStatus"]
            if status == "Filled":
                btc = Decimal(order["cumExecQty"])
                usd = Decimal(order["cumExecValue"])
                if not btc.is_finite() or not usd.is_finite() or btc <= 0 or usd <= 0:
                    raise RuntimeError(f"Bybit order {order_id} has invalid fill amounts")
                return BtcOrderResult(usd=usd, btc=btc, price=usd / btc)
            if status in {"Cancelled", "Rejected", "PartiallyFilledCanceled", "Deactivated"}:
                raise RuntimeError(f"Bybit order {order_id} ended with {status}; executed BTC={order.get('cumExecQty', '0')}")
        if attempt == MAX_RETRIES:
            break
        time.sleep(1)
    raise RuntimeError(f"Bybit order {order_id} was not filled in time")


def get_btc_prices():
    result = _request("GET", "/v5/market/tickers", {"category": "spot", "symbol": SYMBOL})
    for ticker in result.get("list", []):
        if ticker["symbol"] == SYMBOL:
            return Decimal(ticker["ask1Price"]), Decimal(ticker["bid1Price"])
    raise RuntimeError(f"Bybit returned no ticker for {SYMBOL}")


def buy_btc(usd_amount):
    rules = _symbol_info()["lotSizeFilter"]
    amount = _rounded_amount(usd_amount, rules["quotePrecision"])
    if amount < Decimal(rules["minOrderAmt"]):
        raise LessThanMinimumAmountException("Bybit buy amount is below minimum order value")
    return _place_market_order("Buy", "quoteCoin", amount)


def sell_btc(btc_amount):
    rules = _symbol_info()["lotSizeFilter"]
    amount = _rounded_amount(btc_amount, rules["basePrecision"])
    # Bybit enforces the live minimum order value when executing the market sell.
    maximum = Decimal(rules["maxMarketOrderQty"])
    if amount > maximum:
        raise ValueError("Bybit sell amount exceeds maximum market order quantity")
    return _place_market_order("Sell", "baseCoin", amount)
