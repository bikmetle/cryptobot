import csv
from datetime import datetime

filename = "BitcoinHistoricalData.csv"
daily_buy_usd = 5

rows = []

with open(filename, newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        date = datetime.strptime(row["Date"], "%m/%d/%Y").date()
        price = float(row["Price"].replace(",", ""))
        rows.append((date, price))

# Sort from oldest date to newest date
rows.sort()

total_spent = 0
total_btc = 0

for date, price in rows:
    total_spent += daily_buy_usd
    total_btc += daily_buy_usd / price

    if date.day == 6 and date.month == 6:
        current_value = total_btc * price

        print(f"Total money spent: ${total_spent:,.2f}")
        print(f"Current btc price: ${price:,.2f}")
        print(f"Total Bitcoin owned: {total_btc:.8f} BTC")
        print(f"Current value: ${current_value:,.2f}")
        print(f"Profit/Loss: ${current_value - total_spent:,.2f}\n\n")


'''
Total money spent: $1,825.00
Current btc price: $31,367.60
Total Bitcoin owned: 0.04348148 BTC
Current value: $1,363.91
Profit/Loss: $-461.09


Total money spent: $3,650.00
Current btc price: $27,230.20
Total Bitcoin owned: 0.12832596 BTC
Current value: $3,494.34
Profit/Loss: $-155.66


Total money spent: $5,480.00
Current btc price: $70,791.50
Total Bitcoin owned: 0.17603389 BTC
Current value: $12,461.70
Profit/Loss: $6,981.70


Total money spent: $7,305.00
Current btc price: $104,308.30
Total Bitcoin owned: 0.19953319 BTC
Current value: $20,812.97
Profit/Loss: $13,507.97


Total money spent: $9,130.00
Current btc price: $60,774.30
Total Bitcoin owned: 0.21984040 BTC
Current value: $13,360.65
Profit/Loss: $4,230.65
'''
