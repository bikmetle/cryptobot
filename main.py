import asyncio
from datetime import date, datetime
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from database import SessionLocal
from models import Company


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
                tg_group_id=message.chat.id,    
                created_at = date(2021, 6, 6),
                # created_at = datetime.now()
            )

            session.add(company)
            session.commit()

        await message.answer(
            "Successfully initiated"
        )


async def main() -> None:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(token=bot_token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
