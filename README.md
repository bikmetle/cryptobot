# CryptoBot

CryptoBot is a small experimental Bitcoin trading bot built to test one simple investment theory.

The bot is not financial advice. It is an experiment, and it should only be used with an amount of money you are comfortable losing.

The experiment started on June 15, 2026. Public results are posted in the Telegram group:

https://t.me/+VS7_2TaA1OUxNmI0

## Trading Theory

The strategy is intentionally simple:

1. Make only one trading decision per day.
2. Buy a small amount of BTC every day.
3. Each day, check whether any previous buy can be sold with a target profit of 10% per year.
4. If a profitable sell is possible, sell that position, but keep today's daily buy amount invested.

In other words, the bot tries to keep buying consistently while closing older positions only when they reach the target annualized return.

## What The Bot Does

- Places BTC/USDT spot market orders through Bybit, Binance, or Bitget.
- Runs one scheduled trading cycle per day.
- Stores trades and balances in a local SQLite database.
- Sends daily trade results to a Telegram group.
- Sends errors to the configured Telegram admin.
- Includes a small visualization script for saved trade history.

## Project Structure

```text
app/
├── main.py                 # Telegram commands and daily scheduler
├── config.py               # Environment settings
├── exchanges/              # Exchange clients, simulator, and order types
├── trading/                # Trading service, calculations, and exceptions
└── db/                     # SQLAlchemy models, sessions, and queries
scripts/
└── visualize.py            # Saved trade charts
tests/                      # Automated tests
alembic/                    # Database migrations
data/                       # Docker database volume
```

Run commands from the project root. Keep `.env` there; the database paths remain unchanged.

## Configuration

Copy `.env.example` to `.env` at the project root and fill in the required values. The example defaults to `ENV=DEV` for simulated orders; set `ENV=PROD` to use the selected exchange.

```bash
cp .env.example .env
```

Available settings:

```env
ENV=DEV
EXCHANGE=bybit

BITGET_PASSPHRASE=
BITGET_API_KEY=
BITGET_SECRET_KEY=

BINANCE_API_KEY=
BINANCE_SECRET_KEY=

# Bybit HMAC API (Spot trading)
BYBIT_API_KEY=
BYBIT_SECRET_KEY=
BYBIT_BASE_URL=https://api.bybit.com

BOT_TOKEN=
GROUP_TG_ID=
ADMIN_TG_ID=

INTEREST=10
INFLATION=3
MIN_PLATFORM_USD=1
DAILY_BUY_USD=
```

### Environment Variables

- `ENV`: `PROD` uses the selected real exchange; `DEV` and `TEST` use simulated orders.
- `EXCHANGE`: `bybit` (default), `binance`, or `bitget`, case insensitive.
- `BITGET_PASSPHRASE`, `BITGET_API_KEY`, `BITGET_SECRET_KEY`: Bitget API credentials.
- `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`: Binance HMAC API credentials with Spot trading enabled; no passphrase is needed.
- `BYBIT_API_KEY`, `BYBIT_SECRET_KEY`: Bybit HMAC API credentials with Spot trading enabled.
- `BYBIT_BASE_URL`: Optional API endpoint, default `https://api.bybit.com`; use the regional endpoint for your account (for example, `https://api.bybit.id` for Indonesia).
- `BOT_TOKEN`: Telegram bot token.
- `GROUP_TG_ID`: Telegram group or channel ID where daily results are posted.
- `ADMIN_TG_ID`: Telegram user ID that receives error messages.
- `INTEREST`: Target yearly profit percentage for selling a position.
- `INFLATION`: Yearly increase applied to the daily buy amount.
- `MIN_PLATFORM_USD`: Minimum USD difference required before placing an order.
- `DAILY_BUY_USD`: Base amount to invest each day.

To switch exchanges, save the credentials for the exchanges you use, change `EXCHANGE` in `.env`, and restart the bot. With Docker Compose, run `docker compose up -d --force-recreate`. Set `EXCHANGE=bitget` or `EXCHANGE=binance` explicitly to keep using either exchange.

Binance reads BTC/USDT precision and quantity filters from the exchange and rounds order amounts down. Its current minimum notional rules still apply; configure `MIN_PLATFORM_USD` and `DAILY_BUY_USD` accordingly. See the [Binance order documentation](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints) and [symbol filters](https://developers.binance.com/docs/binance-spot-api-docs/filters).

Bybit uses V5 Spot market orders: buys spend USDT and sells specify BTC. Amounts round down using the current instrument precision, and the client polls the accepted order ID for executed BTC and USDT amounts. Minimum-order rejections remain skippable; other API errors, partial cancellations, and fill timeouts stop the trading cycle without resubmitting the order. Recorded fill amounts are gross, before fees. See the [Bybit order API](https://bybit-exchange.github.io/docs/v5/order/create-order) and [authentication and regional endpoints](https://bybit-exchange.github.io/docs/v5/guide).

Switching keeps the same local trade history and accounting. It does not transfer BTC or USDT between exchange accounts; fund the selected account to cover the positions tracked by the bot.

## Running

Install the project dependencies in your Python environment, configure `.env`, then run:

```bash
python -m app.main
```

To run the tests:

```bash
python -m pytest -q
```

The bot polls Telegram commands and also starts a background task that runs the trading cycle once per day at midnight UTC.

## Running With Docker

Build and start the bot with Docker Compose:

```bash
docker compose up --build -d
```

The Compose setup reads `.env` from the project root and stores the SQLite database in `./data/cryptobot.db` on your machine, mounted inside the container at `/data/cryptobot.db`. On startup, the container runs `alembic upgrade head` before starting the bot.

To stop the bot:

```bash
docker compose down
```

## Telegram Commands

- `/start`: basic bot response.
- `/id`: returns your Telegram user ID and the current chat ID.

## Visualization

To generate charts from saved trades:

```bash
python -m scripts.visualize
```

The script saves:

- `entry_exit_usd_amounts.png`
- `entry_prices.png`

If `matplotlib` is missing, install it first:

```bash
pip install matplotlib
```

## Risk Warning

This project uses real market orders when connected to real exchange credentials. Crypto prices can move quickly, market orders may fill at unexpected prices, and bugs or wrong configuration can lose money.

Use small amounts, test carefully, and never run the bot with funds you cannot afford to lose.


