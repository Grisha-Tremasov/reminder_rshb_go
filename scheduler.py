import datetime
from aiogram import Bot
import database as db
import yandex_sheets


def count_working_days_between(start_date: datetime.date, target_date: datetime.date) -> int:
    """Считает количество рабочих дней между датами (Пн-Пт)."""
    if target_date < start_date:
        return -1

    cur = start_date + datetime.timedelta(days=1)
    work_days = 0
    while cur <= target_date:
        if cur.weekday() < 5:
            work_days += 1
        cur += datetime.timedelta(days=1)
    return work_days


def build_status_message(name: str, days_calendar: float | None) -> str:
    """Формирует понятный текст уведомления по остатку дней."""
    if days_calendar is None:
        return f"👤 **{name}**, в таблице пока не указан срок смены пароля."

    today = datetime.date.today()
    days_cal_int = int(days_calendar)

    if days_cal_int < 0:
        return (
            f"🚨 **Внимание, {name}!**\n\n"
            f"Срок действия вашего пароля уже **истёк** ({abs(days_cal_int)} дн. назад)!\n"
            f"Срочно смените пароль учетной записи!"
        )

    expiry_date = today + datetime.timedelta(days=days_cal_int)
    work_days_left = count_working_days_between(today, expiry_date)

    if 0 <= work_days_left <= 3:
        return (
            f"⚠️ **Внимание, {name}!**\n\n"
            f"До блокировки учетной записи осталось: **{work_days_left}** рабочих дн. "
            f"(календарных: {days_cal_int} дн., дата: {expiry_date.strftime('%d.%m.%Y')}).\n\n"
            f"Пожалуйста, смените пароль заблаговременно!"
        )

    return (
        f"✅ **{name}**, всё в порядке.\n"
        f"До смены пароля осталось **{work_days_left}** рабочих дн. "
        f"(календарных: {days_cal_int} дн., дата: {expiry_date.strftime('%d.%m.%Y')})."
    )


async def run_daily_check(bot: Bot):
    today = datetime.date.today()
    if today.weekday() >= 5:
        return

    users = db.get_all_users()
    if not users:
        return

    try:
        sheet_data = yandex_sheets.get_sheet_data()
    except Exception as e:
        print(f"Ошибка получения таблицы при проверке: {e}")
        return

    for chat_id, full_name in users:
        matched_name = next(
            (k for k in sheet_data.keys() if k.lower() == full_name.lower()), None
        )
        if not matched_name:
            continue

        days_calendar = sheet_data[matched_name]
        if days_calendar is None:
            continue

        today = datetime.date.today()
        expiry_date = today + datetime.timedelta(days=int(days_calendar))
        work_days = count_working_days_between(today, expiry_date)

        # Отправляем только если просрочен или <= 3 рабочих дней
        if days_calendar < 0 or (0 <= work_days <= 3):
            msg = build_status_message(matched_name, days_calendar)
            try:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            except Exception as e:
                print(f"Не удалось отправить пользователю {chat_id}: {e}")
