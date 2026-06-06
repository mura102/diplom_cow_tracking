import os
import psycopg2

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv():
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

# Те же значения что в database.py твоего проекта
DB_NAME     = os.environ.get('DB_NAME',     'cow_tracking_db')
DB_USER     = os.environ.get('DB_USER',     'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_HOST     = os.environ.get('DB_HOST',     'localhost')
DB_PORT     = os.environ.get('DB_PORT',     '5432')


def get_connection():
    """Возвращает psycopg2-соединение с cow_tracking_db."""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT)
    )
    # UTF-8 как в основном database.py
    cursor = conn.cursor()
    cursor.execute("SET client_encoding TO 'UTF8'")
    cursor.close()
    return conn


def get_default_cow_number() -> int:
    """
    Возвращает cow_number первой активной коровы из твоей БД.
    Если коров нет — возвращает 1 (безопасный fallback).
    """
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT cow_number FROM cows "
            "WHERE cow_number IS NOT NULL "
            "ORDER BY cow_number LIMIT 1"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row[0] if row else 1
    except Exception:
        return 1