import datetime
from aiogram import Bot
import database as db
import yandex_sheets


def count_working_days_between(start_date: datetime.date, target_date: datetime.date) -> int:
    """Считает рабочие дни (пн-пт) между start_date (исключая) и target_date (включая)."""
    if target_date < start_date:
        return -1

    cur = start_date + datetime.timedelta(days=1)
    work_days = 0
    while cur <= target_date:
        if cur.weekday() < 5:  # 0..4 = Пн-Пт
            work_days += 1
        cur += datetime.timedelta(days=1)
    return work_days


async def run_daily_check(bot: Bot):
    today = datetime.date.today()

    # В субботу и воскресенье уведомления не шлем
    if today.weekday() >= 5:
        return

    users = db.get_all_users()
    if not users:
        return

    try:
        sheet_data = yandex_sheets.get_sheet_data()
    except Exception as e:
        print(f"Ошибка получения таблицы при ежедневной проверке: {e}")
        return

    for chat_id, full_name in users:
        # Ищем пользователя без учета регистра
        matched_name = next(
            (k for k in sheet_data.keys() if k.lower() == full_name.lower()), None
        )

        if not matched_name:
            continue

        days_calendar = sheet_data[matched_name]
        if days_calendar is None:
            continue

        # Дата окончания пароля по календарю
        expiry_date = today + datetime.timedelta(days=int(days_calendar))

        # Считаем, сколько осталось именно РАБОЧИХ дней
        work_days_left = count_working_days_between(today, expiry_date)

        # Условие: если пароль просрочен или осталось <= 3 рабочих дней
        if work_days_left <= 0 and days_calendar <= 0:
            text = (
                f"🚨 **Внимание, {matched_name}!**\n\n"
                f"Срок действия вашего пароля уже **истёк** ({int(days_calendar)} дн. назад)!\n"
                f"Срочно смените пароль учетной записи!"
            )
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

        elif 0 <= work_days_left <= 3:
            text = (
                f"⚠️ **Напоминание о смене пароля**\n\n"
                f"Уважаемый(-ая) {matched_name},\n"
                f"До блокировки учетной записи осталось **{work_days_left}** рабочих дн. "
                f"(по календарю: {int(days_calendar)} дн., до {expiry_date.strftime('%d.%m.%Y')}).\n\n"
                f"Пожалуйста, смените пароль вовремя."
            )
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
