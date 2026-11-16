import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
import database as db
import yandex_sheets

MSK_TZ = ZoneInfo("Europe/Moscow")


def get_msk_today() -> datetime.date:
    return datetime.datetime.now(MSK_TZ).date()


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
    if days_calendar is None:
        return f"👤 **{name}**, в таблице пока не указан срок смены пароля."

    today = get_msk_today()
    days_cal_int = int(days_calendar)

    if days_cal_int <= 0:
        overdue_str = f"{abs(days_cal_int)} дн. назад" if days_cal_int < 0 else "сегодня"
        return (
            f"🚨 **Внимание, {name}!**\n\n"
            f"Срок действия вашего пароля **истёк** ({overdue_str})!\n"
            f"Учетная запись может быть заблокирована. Срочно смените пароль!"
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
    today = get_msk_today()
    today_str = today.strftime("%Y-%m-%d")

    # В субботу и воскресенье рассылок нет
    if today.weekday() >= 5:
        return

    users = db.get_all_users()
    if not users:
        return

    try:
        sheet_data = yandex_sheets.get_sheet_data()
    except Exception as e:
        print(f"Ошибка получения таблицы: {e}")
        return

    for chat_id, full_name, last_notified_date, expired_notified in users:
        matched_name = next(
            (k for k in sheet_data.keys() if k.lower() == full_name.lower()), None
        )
        if not matched_name:
            continue

        days_calendar = sheet_data[matched_name]
        if days_calendar is None:
            continue

        days_cal_int = int(days_calendar)

        # СЦЕНАРИЙ 1: Пароль просрочен (<= 0)
        if days_cal_int <= 0:
            # Если еще НЕ слали финальное предупреждение о просрочке
            if not expired_notified:
                msg = build_status_message(matched_name, days_calendar)
                try:
                    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
                    # Помечаем, что уведомили о просрочке (больше слать не будем)
                    db.mark_notified(chat_id, today_str, is_expired=True)
                except Exception as e:
                    print(f"Не удалось отправить пользователю {chat_id}: {e}")
            continue

        # СЦЕНАРИЙ 2: Пароль активен (> 0)
        # Если ранее висел флаг просрочки — сбрасываем его (пароль обновили)
        if expired_notified:
            db.reset_expired_flag(chat_id)

        # Если сегодня уже отправляли напоминание — пропускаем
        if last_notified_date == today_str:
            continue

        expiry_date = today + datetime.timedelta(days=days_cal_int)
        work_days = count_working_days_between(today, expiry_date)

        # Напоминаем каждый рабочий день, пока осталось <= 3 рабочих дней
        if 0 <= work_days <= 3:
            msg = build_status_message(matched_name, days_calendar)
            try:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
                db.mark_notified(chat_id, today_str, is_expired=False)
            except Exception as e:
                print(f"Не удалось отправить пользователю {chat_id}: {e}")

