import csv
import subprocess
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def reset_database() -> None:
    (BASE_DIR / "cryptobot.db").unlink(missing_ok=True)
    subprocess.run(["alembic", "upgrade", "head"], cwd=BASE_DIR, check=True)


reset_database()

from consts import DAILY_BUY_USD
from database import SessionLocal
from db_helpers import enter, exit, update_company
from models import Company
from utils import _to_decimal

with SessionLocal() as session:
    company = Company(
    )

    session.add(company)
    session.commit()


filename = "BitcoinHistoricalData.csv"

rows = []

with open(filename, newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        date = datetime.strptime(row["Date"], "%m/%d/%Y").date()
        price = float(row["Price"].replace(",", ""))
        rows.append((date, price))

# Sort from oldest date to newest date
rows.sort()

for date, price in rows:
    price = _to_decimal(price)
    with SessionLocal() as session:
        to_spend = _to_decimal(DAILY_BUY_USD)
        btc = to_spend / price
        entry_trade = enter(session, price)
        company = update_company(session, entry_trade.entry_usd_amount, entry_trade.btc_amount, 1)

        if exit_trade:= exit(session, price):
            company = update_company(session, -exit_trade.exit_usd_amount, -exit_trade.btc_amount, 1)

    if date.day == 6 and date.month == 6:
        current_value = company.btc * price

        print(f"Total money spent: ${company.spent:,.2f}")
        print(f"Current btc price: ${price:,.2f}")
        print(f"Total Bitcoin owned: {company.btc:.8f} BTC")
        print(f"Current value: ${current_value:,.2f}")
        print(f"Profit/Loss: ${current_value - company.spent:,.2f}\n\n")
