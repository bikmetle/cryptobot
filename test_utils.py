from datetime import date, datetime, timedelta

from utils import is_price_above_compound_interest


def test_is_price_above_compound_interest_returns_true_when_price_beats_target():
    entry_date = date.today() - timedelta(days=365)

    assert is_price_above_compound_interest(121, 100, entry_date, 20) is True


def test_is_price_above_compound_interest_returns_false_when_price_does_not_beat_target():
    entry_date = datetime.combine(date.today() - timedelta(days=365), datetime.min.time())

    assert is_price_above_compound_interest(120, 100, entry_date, 20) is False
