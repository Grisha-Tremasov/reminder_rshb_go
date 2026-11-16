import sqlite3

DB_PATH = "bot.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                last_notified_date TEXT,
                expired_notified INTEGER DEFAULT 0
            )
            """
        )
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_notified_date TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN expired_notified INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.commit()


def save_user(chat_id: int, full_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO users (chat_id, full_name)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET full_name = excluded.full_name
            """,
            (chat_id, full_name.strip()),
        )
        conn.commit()


def get_all_users() -> list[tuple[int, str, str | None, int]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, full_name, last_notified_date, COALESCE(expired_notified, 0) FROM users")
        return cursor.fetchall()


def get_user(chat_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT full_name FROM users WHERE chat_id = ?", (chat_id,))
        return cursor.fetchone()


def mark_notified(chat_id: int, date_str: str, is_expired: bool = False):
    with sqlite3.connect(DB_PATH) as conn:
        if is_expired:
            conn.execute(
                "UPDATE users SET last_notified_date = ?, expired_notified = 1 WHERE chat_id = ?",
                (date_str, chat_id),
            )
        else:
            conn.execute(
                "UPDATE users SET last_notified_date = ?, expired_notified = 0 WHERE chat_id = ?",
                (date_str, chat_id),
            )
        conn.commit()


def reset_expired_flag(chat_id: int):
    """Сбрасывает флаг просрочки, когда пароль обновили и дни снова стали > 0."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET expired_notified = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()

