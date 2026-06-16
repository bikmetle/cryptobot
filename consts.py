from datetime import timezone
import os
from dotenv import load_dotenv

load_dotenv()


PASSPHRASE = os.getenv("PASSPHRASE")
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

INTEREST = os.getenv("INTEREST")
INFLATION = os.getenv("INFLATION")
MIN_PLATFORM_USD = os.getenv("MIN_PLATFORM_USD")
DAILY_BUY_USD = os.getenv("DAILY_BUY_USD")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_TG_ID = os.getenv("GROUP_TG_ID")
ADMIN_TG_ID = os.getenv("ADMIN_TG_ID")

TZINFO=timezone.utc
