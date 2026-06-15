import asyncio
from datetime import datetime, time, timedelta, timezone
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from consts import ADMIN_TG_ID, BOT_TOKEN, GROUP_TG_ID
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


async def daily_trade(bot: Bot, group_tg_id: str, admin_tg_id: str) -> None:
    while True:
        now = datetime.now(timezone.utc)
        next_run = (
            datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
            + timedelta(days=1)
        )

        await asyncio.sleep((next_run - now).total_seconds())
        try:
            with SessionLocal() as session:
                msg = trade(session)
            await bot.send_message(group_tg_id, msg)
        except Exception as e:
            await bot.send_message(admin_tg_id, f"daily trade error:\n{e}\n#error")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    group_tg_id = GROUP_TG_ID
    if not group_tg_id:
        raise RuntimeError("GROUP_TG_ID is not set")

    admin_tg_id = ADMIN_TG_ID
    if not admin_tg_id:
        raise RuntimeError("ADMIN_TG_ID is not set")

    bot = Bot(token=BOT_TOKEN)
    daily_task = asyncio.create_task(daily_trade(bot, group_tg_id, admin_tg_id))

    try:
        await dp.start_polling(bot)
    finally:
        daily_task.cancel()
        await asyncio.gather(daily_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
