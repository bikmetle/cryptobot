from sqlalchemy import select

from database import SessionLocal
from models import BitcoinTrade


def main() -> None:
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit("Install matplotlib first: pip install matplotlib") from exc

    with SessionLocal() as session:
        trades = session.scalars(
            select(BitcoinTrade).order_by(BitcoinTrade.entered_at.asc())
        ).all()

    entry_dates = [trade.entered_at for trade in trades]
    entry_usd_amounts = [float(trade.entry_usd_amount) for trade in trades]
    entry_prices = [float(trade.entry_price) for trade in trades]

    exited_trades = [
        trade
        for trade in trades
        if trade.exited_at is not None and trade.exit_usd_amount is not None
    ]
    exit_dates = [trade.exited_at for trade in exited_trades]
    exit_usd_amounts = [float(trade.exit_usd_amount) for trade in exited_trades]

    amounts_figure = plt.figure(figsize=(18, 6))
    for trade in exited_trades:
        plt.plot(
            [trade.entered_at, trade.exited_at],
            [float(trade.entry_usd_amount), float(trade.exit_usd_amount)],
            color="gray",
            linewidth=0.7,
            alpha=0.5,
        )

    plt.scatter(entry_dates, entry_usd_amounts, label="Entry USD amount")
    plt.scatter(exit_dates, exit_usd_amounts, label="Exit USD amount")
    plt.xlabel("Date")
    plt.ylabel("USD amount")
    plt.title("Entry and exit USD amounts by date")
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    amounts_figure.autofmt_xdate()
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    prices_figure = plt.figure(figsize=(18, 6))
    plt.plot(entry_dates, entry_prices, marker="o", label="Entry price")
    plt.xlabel("Date")
    plt.ylabel("Entry price")
    plt.title("Entry price by date")
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    prices_figure.autofmt_xdate()
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    amounts_figure.savefig("entry_exit_usd_amounts.png")
    prices_figure.savefig("entry_prices.png")

    if "agg" not in plt.get_backend().lower():
        plt.show()

    print("Saved graphs: entry_exit_usd_amounts.png, entry_prices.png")


if __name__ == "__main__":
    main()
