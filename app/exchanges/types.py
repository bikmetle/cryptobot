from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BtcOrderResult:
    usd: Decimal
    btc: Decimal
    price: Decimal
