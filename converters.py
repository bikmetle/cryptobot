from decimal import Decimal


def _to_decimal(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value))
