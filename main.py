import asyncio
from datetime import date, datetime, time, timedelta, timezone
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from database import SessionLocal
from models import Company
from trading import get_rows, trade


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("Hello! Use /id to get your Telegram ID.")


@dp.message(Command("id"))
async def get_id(message: Message) -> None:
    await message.answer(
        f"Your ID: {message.from_user.id}\nChat ID: {message.chat.id}"
    )


@dp.message(Command("init"))
async def get_id(message: Message) -> None:
    if message.chat.type != "private":
        with SessionLocal() as session:
            company = Company(
                created_at = date(2021, 6, 6),
                # created_at = datetime.now()
            )

            session.add(company)
            session.commit()

        await message.answer(
            "Successfully initiated"
        )


async def daily_trade(bot: Bot, group_id: int, admin_id: int) -> None:
    while True:
        now = datetime.now(timezone.utc)
        next_run = (
            datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
            + timedelta(days=1)
        )

        await asyncio.sleep((next_run - now).total_seconds())
        try:
            msg = trade()
            await bot.send_message(group_id, msg)
        except Exception as e:
            await bot.send_message(admin_id, f"daily trade error:\n{e}\n#error")


async def main() -> None:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    group_id = os.getenv("GROUP_TG_ID")
    if not group_id:
        raise RuntimeError("GROUP_TG_ID is not set")

    admin_id = os.getenv("ADMIN_TG_ID")
    if not group_id:
        raise RuntimeError("ADMIN_TG_ID is not set")

    bot = Bot(token=bot_token)
    daily_task = asyncio.create_task(daily_trade(bot, int(group_id), int(admin_id)))

    try:
        await dp.start_polling(bot)
    finally:
        daily_task.cancel()
        await asyncio.gather(daily_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
