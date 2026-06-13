from decimal import Decimal

from utils import calculate_usd_amount_from_price_range, calculate_usd_amount


def test_calculate_usd_amount_from_price_range_returns_minimum_when_range_is_missing():
    assert calculate_usd_amount_from_price_range(None, None) == Decimal("1")


def test_calculate_usd_amount_from_price_range_scales_by_low_to_high_ratio():
    assert calculate_usd_amount_from_price_range(Decimal("50"), Decimal("100")) == Decimal("8.0")


def test_calculate_usd_amount_from_price_range_returns_minimum_when_prices_match():
    assert calculate_usd_amount_from_price_range(Decimal("100"), Decimal("100")) == Decimal("1")


def test_calculate_usd_amount_from_trade_counts_returns_maximum_when_no_trades_exist():
    assert calculate_usd_amount(0, 0) == Decimal("15")


def test_calculate_usd_amount_from_trade_counts_scales_down_by_exit_ratio():
    assert calculate_usd_amount(10, 5) == Decimal("8.0")
