from datetime import timezone
from enum import StrEnum
import os
from dotenv import load_dotenv

load_dotenv()


class Environment(StrEnum):
    PROD = "PROD"
    DEV = "DEV"
    TEST = "TEST"


ENV = Environment(os.getenv("ENV", Environment.DEV))

class Exchange(StrEnum):
    BITGET = "bitget"
    BINANCE = "binance"


EXCHANGE = Exchange(os.getenv("EXCHANGE", Exchange.BINANCE).strip().lower())

BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE")
BITGET_API_KEY = os.getenv("BITGET_API_KEY")
BITGET_SECRET_KEY = os.getenv("BITGET_SECRET_KEY")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

INTEREST = os.getenv("INTEREST")
INFLATION = os.getenv("INFLATION")
MIN_PLATFORM_USD = os.getenv("MIN_PLATFORM_USD")
DAILY_BUY_USD = os.getenv("DAILY_BUY_USD")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_TG_ID = os.getenv("GROUP_TG_ID")
ADMIN_TG_ID = os.getenv("ADMIN_TG_ID")

TZINFO=timezone.utc
