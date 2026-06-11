# to do make tg group to track all trades
# every buy and sell and show total
import csv
import subprocess
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def reset_database() -> None:
    (BASE_DIR / "cryptobot.db").unlink(missing_ok=True)
    subprocess.run(["alembic", "upgrade", "head"], cwd=BASE_DIR, check=True)


reset_database()

from database import SessionLocal
from db_helpers import enter, exit, get_company, get_trades_count, update_company
from models import Company
from utils import _to_decimal, calculate_usd_amount_from_trade_counts

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
        company_spent = _to_decimal(0)
        if exit_trade:= exit(session, price, date):
            exit_usd_amount = exit_trade.exit_usd_amount
            if exit_usd_amount is None:
                raise ValueError("Exit trade is missing exit_usd_amount")

            company = update_company(session, -exit_usd_amount, -exit_trade.btc_amount, 1)

        else:
            company = get_company(session, 1)
            company_spent = company.spent

        total_trades, exited_trades = get_trades_count(session)
        usd_amount = calculate_usd_amount_from_trade_counts(total_trades, exited_trades, company_spent)
        entry_trade = enter(session, price, usd_amount, date)
        company = update_company(session, entry_trade.entry_usd_amount, entry_trade.btc_amount, 1)

    if date.day == 6 and date.month == 6:
        current_value = company.btc * price

        print(f"\nTotal money spent: ${company.spent:,.2f}")
        print(f"Current btc price: ${price:,.2f}")
        print(f"Total Bitcoin owned: {company.btc:.8f} BTC")
        print(f"Current value: ${current_value:,.2f}")
        print(f"Profit/Loss: ${current_value - company.spent:,.2f}")
        print(f"Usd amount: ${usd_amount:,.2f}\n")
