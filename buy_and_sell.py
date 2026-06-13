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

from consts import MIN_PLATFORM_USD
from database import SessionLocal
from db_helpers import enter, exit, get_company, get_trade_to_exit, get_trades_count, update_company
from models import Company, TradeKind
from utils import _to_decimal, calculate_usd_amount

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
        current_price = float(row["Price"].replace(",", ""))
        rows.append((date, current_price))

# Sort from oldest date to newest date
rows.sort()


for date, price in rows:
    trade_kind = TradeKind.ENTRY
    current_price = _to_decimal(price)
    with SessionLocal() as session:
        trade_to_exit = get_trade_to_exit(session, current_price, date)
        if trade_to_exit:
            exit_btc = trade_to_exit.btc_amount
            exit_usd = current_price*trade_to_exit.btc_amount
            trade_kind = TradeKind.ENTRY

        company = get_company(session, 1)
        total_trades, exited_trades = get_trades_count(session)
        entry_usd = calculate_usd_amount(total_trades, exited_trades, company, trade_kind)
        entry_btc = entry_usd/current_price

        if trade_to_exit:
            exit_trade = exit(session, trade_to_exit, current_price, date)
            company = update_company(session, -exit_trade.exit_usd_amount, -exit_trade.btc_amount, 1)
            usd_delta = entry_usd - exit_usd

            if abs(usd_delta) <= MIN_PLATFORM_USD:
                # api buy min platform usd
                entry_trade = enter(session, current_price, entry_usd+MIN_PLATFORM_USD-usd_delta, date)

            elif usd_delta > MIN_PLATFORM_USD:
                entry_trade = enter(session, current_price, entry_usd, date)
                # api buy usd_delta
                
            else:
                entry_trade = enter(session, current_price, entry_usd, date)
                # api sell usd_delta

        else:
            entry_trade = enter(session, current_price, entry_usd, date)

        company = update_company(session, entry_trade.entry_usd_amount, entry_trade.btc_amount, 1)

    if date.day == 6 and date.month == 6:
        current_value = company.btc * current_price

        print(f"\nTotal money spent: ${company.spent:,.2f}")
        print(f"Current btc price: ${current_price:,.2f}")
        print(f"Total Bitcoin owned: {company.btc:.8f} BTC")
        print(f"Current value: ${current_value:,.2f}")
        print(f"Profit/Loss: ${current_value - company.spent:,.2f}")
        print(f"Usd amount: ${entry_usd:,.2f}\n")
