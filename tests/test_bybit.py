from decimal import Decimal as D
import hashlib
import hmac
import json
from unittest.mock import Mock
from urllib.parse import parse_qs

import pytest
import requests

import bybit
from consts import Environment
from trading_exceptions import LessThanMinimumAmountException


@pytest.fixture(autouse=True)
def client(monkeypatch):
    monkeypatch.setattr(bybit, "ENV", Environment.PROD)
    monkeypatch.setattr(bybit, "BYBIT_API_KEY", "test-key")
    monkeypatch.setattr(bybit, "BYBIT_SECRET_KEY", "test-secret")
    monkeypatch.setattr(bybit.time, "sleep", lambda _: None)
    transport = Mock()
    monkeypatch.setattr(bybit.requests, "request", transport)
    return transport


def response(result=None, **overrides):
    return Mock(json=Mock(return_value={"retCode": 0, "retMsg": "OK", "result": result or {}, **overrides}))


def symbol_info(**rules):
    return {"list": [{"symbol": "BTCUSDT", "status": "Trading", "lotSizeFilter": {
        "basePrecision": "0.000001", "quotePrecision": "0.01", "minOrderAmt": "5",
        "maxMarketOrderQty": "100", **rules,
    }}]}


def filled(**values):
    return {"list": [{"orderId": "123", "orderStatus": "Filled",
                      "cumExecQty": "0.0001", "cumExecValue": "10", **values}]}


def prepare_order(client, *statuses):
    client.side_effect = [response(symbol_info()), response({"orderId": "123"}),
                          *[response(status) for status in (statuses or (filled(),))]]


def test_prices_use_ask_for_buy_and_bid_for_sell(client):
    client.return_value = response({"list": [{"symbol": "BTCUSDT", "ask1Price": "100001.20", "bid1Price": "100000.10"}]})
    assert bybit.get_btc_prices() == (D("100001.20"), D("100000.10"))
    assert client.call_args.args == ("GET", bybit.BASE_URL + "/v5/market/tickers")
    assert client.call_args.kwargs["headers"] == {}


def test_buy_spends_quote_and_signs_exact_body_and_query(client, monkeypatch):
    monkeypatch.setattr(bybit.time, "time", lambda: 1700000000)
    prepare_order(client)
    order = bybit.buy_btc(D("10.129"))
    assert (order.usd, order.btc, order.price) == (D("10"), D("0.0001"), D("100000"))
    post, get = client.call_args_list[1:]
    assert post.args == ("POST", bybit.BASE_URL + "/v5/order/create")
    assert json.loads(post.kwargs["data"]) == {
        "category": "spot", "symbol": "BTCUSDT", "side": "Buy", "orderType": "Market",
        "qty": "10.12", "marketUnit": "quoteCoin", "isLeverage": 0,
    }
    for call, field in ((post, "data"), (get, "params")):
        headers = call.kwargs["headers"]
        expected = hmac.new(b"test-secret", ("1700000000000test-key5000" + call.kwargs[field]).encode(), hashlib.sha256).hexdigest()
        assert headers["X-BAPI-SIGN"] == expected
        assert headers["X-BAPI-API-KEY"] == "test-key"
        assert headers["X-BAPI-TIMESTAMP"] == "1700000000000"
        assert headers["X-BAPI-RECV-WINDOW"] == "5000"
        assert call.kwargs["timeout"] == 10
    assert post.kwargs["headers"]["Content-Type"] == "application/json"
    assert parse_qs(get.kwargs["params"])["orderId"] == ["123"]


def test_sell_rounds_down_and_uses_base_coin(client):
    prepare_order(client)
    bybit.sell_btc(D("0.00010999"))
    params = json.loads(client.call_args_list[1].kwargs["data"])
    assert (params["side"], params["marketUnit"], params["qty"]) == ("Sell", "baseCoin", "0.000109")


@pytest.mark.parametrize("operation,amount", [("buy_btc", "0"), ("buy_btc", "4.999"), ("buy_btc", "-1"), ("sell_btc", "0.0000009"), ("sell_btc", "-1")])
def test_small_orders_never_submit(client, operation, amount):
    client.return_value = response(symbol_info())
    with pytest.raises(LessThanMinimumAmountException):
        getattr(bybit, operation)(D(amount))
    assert client.call_count == 1


def test_oversized_sell_never_submits(client):
    client.return_value = response(symbol_info())
    with pytest.raises(ValueError, match="maximum"):
        bybit.sell_btc(101)
    assert client.call_count == 1


@pytest.mark.parametrize("code", [170136, 170140])
def test_minimum_errors_preserve_details(client, code):
    client.return_value = response(retCode=code, retMsg="minimum rejection")
    with pytest.raises(LessThanMinimumAmountException, match=f"{code}: minimum rejection"):
        bybit._request("POST", "/v5/order/create", signed=True)


def test_other_api_errors_are_not_skipped(client):
    client.return_value = response(retCode=170131, retMsg="Balance insufficient")
    with pytest.raises(RuntimeError, match="170131: Balance insufficient"):
        bybit._request("POST", "/v5/order/create", signed=True)


def test_empty_and_pending_orders_are_polled_without_resubmitting(client):
    prepare_order(client, {"list": []}, filled(orderStatus="New"), filled(orderStatus="PartiallyFilled"), filled())
    assert bybit.buy_btc(10).price == D("100000")
    assert [c.args[0] for c in client.call_args_list] == ["GET", "POST", "GET", "GET", "GET", "GET"]
    assert all(parse_qs(c.kwargs["params"])["orderId"] == ["123"] for c in client.call_args_list[2:])


@pytest.mark.parametrize("status", ["Cancelled", "Rejected", "PartiallyFilledCanceled", "Deactivated"])
def test_terminal_orders_raise_without_resubmitting(client, status):
    prepare_order(client, filled(orderStatus=status))
    with pytest.raises(RuntimeError, match=f"123 ended with {status}"):
        bybit.buy_btc(10)
    assert client.call_count == 3


@pytest.mark.parametrize("btc,usd", [("0", "10"), ("0.0001", "0"), ("NaN", "10")])
def test_invalid_fills_are_not_recorded(client, btc, usd):
    prepare_order(client, filled(cumExecQty=btc, cumExecValue=usd))
    with pytest.raises(RuntimeError, match="invalid fill"):
        bybit.buy_btc(10)


def test_fill_on_final_retry_succeeds(client):
    prepare_order(client, *([filled(orderStatus="New")] * bybit.MAX_RETRIES), filled())
    assert bybit.buy_btc(10).btc == D("0.0001")
    assert client.call_count == 2 + bybit.MAX_RETRIES + 1


def test_fill_timeout_never_resubmits(client):
    prepare_order(client, *([{"list": []}] * (bybit.MAX_RETRIES + 1)))
    with pytest.raises(RuntimeError, match="123 was not filled in time"):
        bybit.buy_btc(10)
    assert client.call_count == 2 + bybit.MAX_RETRIES + 1
    assert sum(c.args[0] == "POST" for c in client.call_args_list) == 1


def test_submission_timeout_never_resubmits(client):
    client.side_effect = [response(symbol_info()), requests.exceptions.Timeout("unknown execution status")]
    with pytest.raises(requests.exceptions.Timeout):
        bybit.buy_btc(10)
    assert client.call_count == 2


@pytest.mark.parametrize("credential", ["BYBIT_API_KEY", "BYBIT_SECRET_KEY"])
def test_missing_credentials_prevent_signed_request(client, monkeypatch, credential):
    monkeypatch.setattr(bybit, credential, None)
    with pytest.raises(RuntimeError, match="BYBIT_API_KEY and BYBIT_SECRET_KEY"):
        bybit._request("POST", "/v5/order/create", signed=True)
    client.assert_not_called()


@pytest.mark.parametrize("environment", [Environment.TEST, Environment.DEV])
def test_nonproduction_client_cannot_send_requests(client, monkeypatch, environment):
    monkeypatch.setattr(bybit, "ENV", environment)
    with pytest.raises(RuntimeError, match="ENV=PROD"):
        bybit.get_btc_prices()
    client.assert_not_called()


def test_invalid_json(client):
    client.return_value = Mock(json=Mock(side_effect=requests.exceptions.JSONDecodeError("bad", "", 0)))
    with pytest.raises(RuntimeError, match="invalid JSON"):
        bybit.get_btc_prices()


@pytest.mark.parametrize("payload", [[], {}, {"retCode": 0, "result": []}])
def test_malformed_response(client, payload):
    client.return_value = Mock(json=Mock(return_value=payload))
    with pytest.raises(RuntimeError, match="Unexpected Bybit API response"):
        bybit.get_btc_prices()


def test_http_error_is_not_accepted(client):
    client.return_value = response()
    client.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("503")
    with pytest.raises(requests.exceptions.HTTPError):
        bybit.get_btc_prices()


def test_unavailable_symbol_prevents_order(client):
    client.return_value = response({"list": []})
    with pytest.raises(RuntimeError, match="not available"):
        bybit.buy_btc(10)
    assert client.call_count == 1
