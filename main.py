import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

import database as db
import yandex_sheets
import scheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class Registration(StatesGroup):
    waiting_for_name = State()


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    existing_user = db.get_user(message.chat.id)
    if existing_user:
        await message.answer(
            f"Здравствуйте! Вы уже зарегистрированы как:\n**{existing_user[0]}**\n\n"
            f"Если хотите изменить ФИО, напишите новое ФИО в ответном сообщении.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "Здравствуйте! Я бот оповещений о сроке действия паролей.\n\n"
            "Пожалуйста, введите ваше **ФИО полностью** (точно так, как в таблице):",
            parse_mode="Markdown"
        )
    await state.set_state(Registration.waiting_for_name)


@dp.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    user_name = message.text.strip()

    await message.answer("Проверяю наличие сотрудника в таблице...")

    try:
        sheet_data = yandex_sheets.get_sheet_data()

        # Нечувствительный к регистру поиск
        matched = next((k for k in sheet_data.keys() if k.lower() == user_name.lower()), None)

        if not matched:
            await message.answer(
                f"❌ Сотрудник «{user_name}» не найден на листе «УЗ ПРОД».\n"
                f"Проверьте правильность написания ФИО и попробуйте еще раз."
            )
            return

        db.save_user(message.chat.id, matched)
        days = sheet_data[matched]
        days_str = f"{int(days)} дн." if days is not None else "нет данных"

        await message.answer(
            f"✅ Отлично! Вы успешно зарегистрированы как **{matched}**.\n"
            f"Текущий остаток по таблице: **{days_str}**.\n\n"
            f"Каждый рабочий день в 10:00 я буду проверять срок и предупреждать за 3 рабочих дня.",
            parse_mode="Markdown"
        )
        await state.clear()

    except Exception as e:
        await message.answer(f"⚠️ Ошибка при подключении к таблице: {e}")


async def main():
    db.init_db()

    # Настройка планировщика (Пн-Пт в 10:00)
    sched = AsyncIOScheduler(timezone="Europe/Moscow")
    sched.add_job(
        scheduler.run_daily_check,
        trigger=CronTrigger(day_of_week="mon-fri", hour=10, minute=0),
        args=[bot]
    )
    sched.start()

    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
