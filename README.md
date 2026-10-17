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

- Places BTC/USDT spot market orders through Bitget or Binance.
- Runs one scheduled trading cycle per day.
- Stores trades and balances in a local SQLite database.
- Sends daily trade results to a Telegram group.
- Sends errors to the configured Telegram admin.
- Includes a small visualization script for saved trade history.

## Configuration

Create a `.env` file with the required values:

```env
ENV=PROD
EXCHANGE=bitget

PASSPHRASE=
API_KEY=
SECRET_KEY=

BINANCE_API_KEY=
BINANCE_SECRET_KEY=

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
- `EXCHANGE`: `bitget` (default) or `binance`, case insensitive.
- `PASSPHRASE`, `API_KEY`, `SECRET_KEY`: Bitget API credentials. Alternatively use `BITGET_PASSPHRASE`, `BITGET_API_KEY`, and `BITGET_SECRET_KEY`; these take precedence over the original names.
- `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`: Binance HMAC API credentials with Spot trading enabled; no passphrase is needed.
- `BOT_TOKEN`: Telegram bot token.
- `GROUP_TG_ID`: Telegram group or channel ID where daily results are posted.
- `ADMIN_TG_ID`: Telegram user ID that receives error messages.
- `INTEREST`: Target yearly profit percentage for selling a position.
- `INFLATION`: Yearly increase applied to the daily buy amount.
- `MIN_PLATFORM_USD`: Minimum USD difference required before placing an order.
- `DAILY_BUY_USD`: Base amount to invest each day.

To switch exchanges, save both sets of credentials, change `EXCHANGE` in `.env`, and restart the bot. With Docker Compose, run `docker compose up -d --force-recreate`. Existing Bitget configurations continue to work without changes.

Binance reads BTC/USDT precision and quantity filters from the exchange and rounds order amounts down. Its current minimum notional rules still apply; configure `MIN_PLATFORM_USD` and `DAILY_BUY_USD` accordingly. See the [Binance order documentation](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints) and [symbol filters](https://developers.binance.com/docs/binance-spot-api-docs/filters).

Switching keeps the same local trade history and accounting. It does not transfer BTC or USDT between exchange accounts; fund the selected account to cover the positions tracked by the bot.

## Running

Install the project dependencies in your Python environment, configure `.env`, then run:

```bash
python main.py
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
python visualize.py
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
