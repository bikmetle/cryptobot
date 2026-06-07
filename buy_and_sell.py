import csv
from datetime import datetime

from consts import DAILY_BUY_USD
from database import SessionLocal
from db_helpers import add_bitcoin_trade, update_bitcoin_trade_spread, update_company
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
        trade = update_bitcoin_trade_spread(session, price)
        if trade:
            to_spend -= trade.spread_usd

        btc = to_spend / price
        add_bitcoin_trade(session, price, to_spend)
        company = update_company(session, to_spend, btc, 1)

    if date.day == 6 and date.month == 6:
        current_value = company.btc * price

        print(f"Total money spent: ${company.spent:,.2f}")
        print(f"Current btc price: ${price:,.2f}")
        print(f"Total Bitcoin owned: {company.btc:.8f} BTC")
        print(f"Current value: ${current_value:,.2f}")
        print(f"Profit/Loss: ${current_value - company.spent:,.2f}\n\n")
