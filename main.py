import asyncio
from datetime import datetime, time, timedelta
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from consts import ADMIN_TG_ID, BOT_TOKEN, GROUP_TG_ID, TZINFO, ENV
from database import SessionLocal
from trading import trade

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("Hello! Use /id to get your Telegram ID.")


@dp.message(Command("id"))
async def get_id(message: Message) -> None:
    if message.from_user is None:
        await message.answer(f"Chat ID: {message.chat.id}")
        return

    await message.answer(
        f"Your ID: {message.from_user.id}\nChat ID: {message.chat.id}"
    )


@dp.message(Command("trade"))
async def manually_trade(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return

    if not ADMIN_TG_ID:
        await message.answer("ADMIN_TG_ID is not configured.")
        return

    if str(message.from_user.id) != ADMIN_TG_ID:
        await message.answer("You are not authorized to run a manual trade.")
        return

    try:
        with SessionLocal() as session:
            msg = trade(session, datetime.now(TZINFO))

        if GROUP_TG_ID:
            await bot.send_message(GROUP_TG_ID, msg)
        else:
            await message.answer(msg)
    except Exception as e:
        await message.answer(f"Manual trade error:\n{e}\n#error")


async def daily_trade(bot: Bot) -> None:
    while True:
        now = datetime.now(TZINFO)
        next_run = (
            datetime.combine(now.date(), time.min, tzinfo=TZINFO)
            + timedelta(days=1)
        )

        await asyncio.sleep((next_run - now).total_seconds())
        try:
            with SessionLocal() as session:
                msg = trade(session, next_run)
            if not GROUP_TG_ID:
                continue
            await bot.send_message(GROUP_TG_ID, msg)
        except Exception as e:
            if not ADMIN_TG_ID:
                continue
            await bot.send_message(ADMIN_TG_ID, f"daily trade error:\n{e}\n#error")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(token=BOT_TOKEN)
    daily_task = asyncio.create_task(daily_trade(bot))

    try:
        await dp.start_polling(bot)
    finally:
        daily_task.cancel()
        await asyncio.gather(daily_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
