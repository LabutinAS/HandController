# src/database.py
import sqlite3
import hashlib
import time
from pathlib import Path

# Путь к базе данных
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'models' / 'users.db'


def init_db():
    """
    Инициализация базы: создаются таблицы users (с FIO),
    calibration и user_scripts
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Таблица пользователей с FIO
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        fio TEXT NOT NULL
    )''')
    # Таблица калибровок
    c.execute('''
    CREATE TABLE IF NOT EXISTS calibration (
        user_id INTEGER PRIMARY KEY,
        scale REAL NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    # Таблица пользовательских скриптов
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_scripts (
        user_id INTEGER NOT NULL,
        gesture TEXT NOT NULL,
        script TEXT NOT NULL,
        PRIMARY KEY(user_id, gesture),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Простой SHA256-хеш пароля"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_user(username: str, password: str, fio: str) -> bool:
    """Регистрация нового пользователя с FIO"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO users (username, password_hash, fio) VALUES (?, ?, ?)',
            (username, hash_password(password), fio)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> int | None:
    """
    Проверка логина: возвращает user_id или None
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'SELECT id, password_hash FROM users WHERE username = ?',
        (username,)
    )
    row = c.fetchone()
    conn.close()
    if row and row[1] == hash_password(password):
        return row[0]
    return None


def get_user_calibration(user_id: int) -> float | None:
    """Получить сохранённый scale для пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'SELECT scale FROM calibration WHERE user_id = ?',
        (user_id,)
    )
    row = c.fetchone()
    conn.close()
    return float(row[0]) if row else None


def set_user_calibration(user_id: int, scale: float):
    """Сохранить или обновить scale"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        '''INSERT INTO calibration(user_id, scale, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             scale = excluded.scale,
             updated_at = excluded.updated_at''',
        (user_id, scale, now)
    )
    conn.commit()
    conn.close()


def set_user_script(user_id: int, gesture: str, script_path: str):
    """Сохранить или обновить скрипт для жеста и пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''INSERT INTO user_scripts(user_id, gesture, script)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, gesture) DO UPDATE SET
             script = excluded.script''',
        (user_id, gesture, script_path)
    )
    conn.commit()
    conn.close()


def get_user_scripts(user_id: int) -> dict[str, str]:
    """Получить маппинг жест→скрипт для пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'SELECT gesture, script FROM user_scripts WHERE user_id = ?',
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return {gesture: script for gesture, script in rows}

# Вызов init_db() в точке входа приложения гарантирует создание таблиц
