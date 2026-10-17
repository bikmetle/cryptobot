from decimal import Decimal as D
import hashlib
import hmac
from unittest.mock import Mock
from urllib.parse import urlencode

import pytest
import requests

import binance
from consts import Environment
from trading_exceptions import LessThanMinimumAmountException


@pytest.fixture(autouse=True)
def client(monkeypatch):
    monkeypatch.setattr(binance, "ENV", Environment.PROD)
    monkeypatch.setattr(binance, "BINANCE_API_KEY", "test-key")
    monkeypatch.setattr(binance, "BINANCE_SECRET_KEY", "test-secret")
    transport = Mock()
    monkeypatch.setattr(binance.requests, "request", transport)
    return transport


def response(payload, **kwargs):
    return Mock(json=Mock(return_value=payload), **kwargs)


def symbol_info():
    return {"symbols": [{"status": "TRADING", "quoteAssetPrecision": 8, "filters": [
        {"filterType": "LOT_SIZE", "minQty": "0.00001", "maxQty": "9000", "stepSize": "0.00001"},
        {"filterType": "MARKET_LOT_SIZE", "minQty": "0", "maxQty": "100", "stepSize": "0"},
    ]}]}


def filled(**kwargs):
    return {"orderId": 123, "status": "FILLED", "executedQty": "0.0001",
            "cummulativeQuoteQty": "10", **kwargs}


def test_prices_use_ask_for_buy_and_bid_for_sell(client):
    client.return_value = response({"askPrice": "100001.20", "bidPrice": "100000.10"})
    assert binance.get_btc_prices() == (D("100001.20"), D("100000.10"))
    assert client.call_args.args == ("GET", binance.BASE_URL + "/api/v3/ticker/bookTicker")
    assert client.call_args.kwargs["headers"] == {}


def test_buy_spends_quote_and_signs_exact_parameters(client, monkeypatch):
    monkeypatch.setattr(binance.time, "time", lambda: 1700000000)
    client.side_effect = [response(symbol_info()), response(filled())]
    order = binance.buy_btc(D("10.123456789"))
    assert (order.usd, order.btc, order.price) == (D("10"), D("0.0001"), D("100000"))
    call = client.call_args
    assert call.args == ("POST", binance.BASE_URL + "/api/v3/order")
    params = dict(call.kwargs["params"])
    signature = params.pop("signature")
    assert signature == hmac.new(b"test-secret", urlencode(params).encode(), hashlib.sha256).hexdigest()
    assert params == {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET",
                      "quoteOrderQty": "10.12345678", "newOrderRespType": "FULL",
                      "timestamp": 1700000000000, "recvWindow": 5000}
    assert call.kwargs["headers"] == {"X-MBX-APIKEY": "test-key"}
    assert call.kwargs["timeout"] == 10


def test_sell_rounds_down_to_symbol_step(client):
    client.side_effect = [response(symbol_info()), response(filled())]
    binance.sell_btc(D("0.00010999"))
    params = client.call_args.kwargs["params"]
    assert params["side"] == "SELL"
    assert params["quantity"] == "0.0001"
    assert "quoteOrderQty" not in params


def test_market_lot_size_is_also_applied(client):
    info = symbol_info()
    info["symbols"][0]["filters"][1]["stepSize"] = "0.0001"
    client.side_effect = [response(info), response(filled())]
    binance.sell_btc(D("0.000199"))
    assert client.call_args.kwargs["params"]["quantity"] == "0.0001"


@pytest.mark.parametrize("amount", ["0", "-1", "0.000001"])
def test_small_sell_does_not_submit_order(client, amount):
    client.return_value = response(symbol_info())
    with pytest.raises(LessThanMinimumAmountException):
        binance.sell_btc(D(amount))
    assert client.call_count == 1


@pytest.mark.parametrize("message", ["Filter failure: MIN_NOTIONAL", "Filter failure: NOTIONAL"])
def test_minimum_errors_preserve_exchange_message(client, message):
    client.return_value = response({"code": -1013, "msg": message})
    with pytest.raises(LessThanMinimumAmountException, match=message):
        binance._request("POST", "/api/v3/order", signed=True)


def test_other_errors_are_not_treated_as_minimum_rejections(client):
    client.return_value = response({"code": -2010, "msg": "Account has insufficient balance"})
    with pytest.raises(RuntimeError, match="-2010: Account has insufficient balance"):
        binance._request("POST", "/api/v3/order", signed=True)


def test_pending_order_queries_existing_order_without_resubmitting(client, monkeypatch):
    monkeypatch.setattr(binance.time, "sleep", lambda _: None)
    client.side_effect = [response(symbol_info()), response(filled(status="NEW")), response(filled())]
    assert binance.buy_btc(10).price == D("100000")
    assert [c.args[0] for c in client.call_args_list] == ["GET", "POST", "GET"]
    assert client.call_args.kwargs["params"]["orderId"] == 123


def test_expired_partial_order_raises_without_retry(client):
    client.side_effect = [response(symbol_info()), response(filled(status="EXPIRED"))]
    with pytest.raises(RuntimeError, match="123 ended with EXPIRED"):
        binance.buy_btc(10)
    assert client.call_count == 2


def test_missing_credentials_prevent_signed_request(client, monkeypatch):
    monkeypatch.setattr(binance, "BINANCE_API_KEY", None)
    with pytest.raises(RuntimeError, match="BINANCE_API_KEY"):
        binance._request("POST", "/api/v3/order", signed=True)
    client.assert_not_called()


def test_nonproduction_client_cannot_send_requests(client, monkeypatch):
    monkeypatch.setattr(binance, "ENV", Environment.TEST)
    with pytest.raises(RuntimeError, match="ENV=PROD"):
        binance.get_btc_prices()
    client.assert_not_called()


def test_invalid_json_error(client):
    client.return_value = Mock(json=Mock(side_effect=requests.exceptions.JSONDecodeError("bad", "", 0)))
    with pytest.raises(RuntimeError, match="invalid JSON"):
        binance.get_btc_prices()


def test_timeout_does_not_resubmit_order(client):
    client.side_effect = [response(symbol_info()), requests.exceptions.Timeout("unknown execution status")]
    with pytest.raises(requests.exceptions.Timeout):
        binance.buy_btc(10)
    assert [c.args[0] for c in client.call_args_list] == ["GET", "POST"]


def test_fill_timeout_only_queries_existing_order(client, monkeypatch):
    monkeypatch.setattr(binance.time, "sleep", lambda _: None)
    client.side_effect = [response(symbol_info())] + [response(filled(status="NEW")) for _ in range(11)]
    with pytest.raises(RuntimeError, match="123 was not filled in time"):
        binance.buy_btc(10)
    assert sum(c.args[0] == "POST" for c in client.call_args_list) == 1


def test_zero_buy_never_places_order(client):
    client.return_value = response(symbol_info())
    with pytest.raises(LessThanMinimumAmountException):
        binance.buy_btc(D("0.000000001"))
    assert client.call_count == 1


def test_fill_on_final_poll_is_recorded(client, monkeypatch):
    monkeypatch.setattr(binance.time, "sleep", lambda _: None)
    client.side_effect = ([response(symbol_info())]
                          + [response(filled(status="NEW")) for _ in range(10)]
                          + [response(filled())])
    assert binance.buy_btc(10).btc == D("0.0001")
