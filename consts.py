import os
from dotenv import load_dotenv

from converters import _to_decimal

load_dotenv()


PASSPHRASE = os.getenv("PASSPHRASE")
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

INTEREST = _to_decimal(os.getenv("INTEREST"))
INFLATION = _to_decimal(os.getenv("INFLATION"))
MIN_PLATFORM_USD = _to_decimal(os.getenv("MIN_PLATFORM_USD"))
DAILY_BUY_USD = _to_decimal(os.getenv("DAILY_BUY_USD"))
