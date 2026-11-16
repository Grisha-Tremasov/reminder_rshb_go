import asyncio
import datetime
import os
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher
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
            f"Вы уже зарегистрированы как: **{existing_user[0]}**\n\n"
            f"Если хотите изменить ФИО, введите новое ФИО сообщением:",
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            "Здравствуйте! Я бот оповещений о смене пароля учетных записей.\n\n"
            "Пожалуйста, введите ваше **ФИО** (в точности как в таблице):",
            parse_mode="Markdown",
        )
    await state.set_state(Registration.waiting_for_name)


@dp.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    user_name = message.text.strip()
    await message.answer("Проверяю данные в таблице...")

    try:
        sheet_data = yandex_sheets.get_sheet_data()
        matched = next(
            (k for k in sheet_data.keys() if k.lower() == user_name.lower()), None
        )

        if not matched:
            await message.answer(
                f"❌ Сотрудник «{user_name}» не найден в таблице на листе «УЗ ПРОД».\n"
                f"Проверьте написание и введите ФИО снова:"
            )
            return

        db.save_user(message.chat.id, matched)
        days = sheet_data[matched]

        status_text = scheduler.build_status_message(matched, days)

        await message.answer(
            f"✅ Вы успешно зарегистрированы!\n\n"
            f"{status_text}\n\n"
            f"📅 Напоминания приходят по рабочим дням в 10:00 (МСК), если до блокировки 3 рабочих дня или меньше.",
            parse_mode="Markdown",
        )
        await state.clear()

    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обращении к таблице: {e}")


async def startup_catchup():
    """Если бот включился после 10:00 МСК, досылаем пропущенное за сегодня."""
    now_msk = datetime.datetime.now(ZoneInfo("Europe/Moscow"))
    if now_msk.weekday() < 5 and now_msk.hour >= 10:
        print("Запуск проверки пропущенных напоминаний за сегодня...")
        await scheduler.run_daily_check(bot)


async def main():
    db.init_db()

    # Запускаем наверстывание пропущенных сообщений при старте
    asyncio.create_task(startup_catchup())

    # Планировщик на 10:00 по МСК (Пн-Пт)
    sched = AsyncIOScheduler(timezone="Europe/Moscow")
    sched.add_job(
        scheduler.run_daily_check,
        trigger=CronTrigger(day_of_week="mon-fri", hour=10, minute=0),
        args=[bot],
        misfire_grace_time=3600,  # Если задача опоздала до 1 часа — всё равно выполнить
    )
    sched.start()

    print("Бот запущен. Нажмите Ctrl+C для выхода.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

