import sqlite3

DB_PATH = "bot.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_user(chat_id: int, full_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (chat_id, full_name) VALUES (?, ?)",
            (chat_id, full_name.strip()),
        )
        conn.commit()


def get_all_users() -> list[tuple[int, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, full_name FROM users")
        return cursor.fetchall()


def get_user(chat_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT full_name FROM users WHERE chat_id = ?", (chat_id,))
        return cursor.fetchone()
