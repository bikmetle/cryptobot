# to do make tg group to track all trades
# every buy and sell and show total

#daily
#weekly
#monthly
#quarter
#yearly

import csv
import subprocess
from datetime import datetime, date
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def reset_database() -> None:
    (BASE_DIR / "cryptobot.db").unlink(missing_ok=True)
    subprocess.run(["alembic", "upgrade", "head"], cwd=BASE_DIR, check=True)


reset_database()

from consts import MIN_PLATFORM_USD
from database import SessionLocal
from db_helpers import enter, exit, get_company, get_trade_to_exit, update_company
from models import Company
from utils import _to_decimal, calculate_usd_amount


with SessionLocal() as session:
    company = Company(
        created_at = date(2021, 6, 6)
    )

    session.add(company)
    session.commit()


filename = "BitcoinHistoricalData.csv"

rows = []

with open(filename, newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        date = datetime.strptime(row["Date"], "%m/%d/%Y").date()
        entry_price = float(row["Price"].replace(",", ""))
        rows.append((date, entry_price))

# Sort from oldest date to newest date
rows.sort()

for date, price in rows:
    entry_price = _to_decimal(price)
    exit_price = _to_decimal(price)
    with SessionLocal() as session:
        company = get_company(session, 1)
        entry_usd = calculate_usd_amount(company, date)

        trade_to_exit = get_trade_to_exit(session, exit_price, entry_usd, date)
        if trade_to_exit:
            exit_usd = exit_price*trade_to_exit.btc_amount
            exit_btc = trade_to_exit.btc_amount
            entry_btc = entry_usd / entry_price # ceil to allowed value by bitget

            exit_trade = exit(session, trade_to_exit, exit_price, date)
            company = update_company(session, exit_trade.exit_usd_amount, -exit_trade.btc_amount, 1)
            usd_delta = entry_usd - exit_usd
            btc_delta = entry_btc - exit_btc

            if usd_delta > 0:
                # api buy btc_delta, exit_btc+respose btc, exit_usd+response usd
                entry_trade = enter(session, entry_price, entry_usd, date)
                
            elif usd_delta < 0:
                # api sell btc_delta, exit_btc-response btc, exit usd-response usd
                entry_trade = enter(session, entry_price, entry_usd, date)

        else:
            # api buy entry usd
            entry_trade = enter(session, entry_price, entry_usd, date)

        company = update_company(session, -entry_trade.entry_usd_amount, entry_trade.btc_amount, 1)

    if date.day == 6 and date.month == 6:
        current_value = company.btc * entry_price

        print(f"\nCompany balance: ${company.balance:,.2f}")
        print(f"Current btc price: ${entry_price:,.2f}")
        print(f"Total Bitcoin owned: {company.btc:.8f} BTC")
        print(f"Current value: ${current_value:,.2f}")
        print(f"Profit/Loss: ${current_value + company.balance:,.2f}")
        print(f"Usd amount: ${entry_usd:,.2f}\n")
