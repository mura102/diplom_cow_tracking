"""
Создание БД cow_tracking_db и таблиц.
Запуск: python -m database.ensure_db
При ошибке пароля запросит его в консоли и сохранит в .env
"""
import getpass
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _load_dotenv():
    env_path = os.path.join(_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _save_password(password: str):
    env_path = os.path.join(_ROOT, ".env")
    lines = []
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as f:
            lines = f.readlines()
    found = False
    out = []
    for line in lines:
        if line.strip().startswith("DB_PASSWORD="):
            out.append(f"DB_PASSWORD={password}\n")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"DB_PASSWORD={password}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(out)
    os.environ["DB_PASSWORD"] = password


def _connect_postgres(password: str):
    import psycopg2

    return psycopg2.connect(
        dbname="postgres",
        user=os.environ.get("DB_USER", "postgres"),
        password=password,
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
    )


def ensure_database():
    _load_dotenv()
    db_name = os.environ.get("DB_NAME", "cow_tracking_db")
    password = os.environ.get("DB_PASSWORD", "")

    for attempt in range(3):
        try:
            conn = _connect_postgres(password)
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Не удалось подключиться: {e}")
            password = getpass.getpass("Пароль PostgreSQL (пользователь postgres): ")
            _save_password(password)

    conn.set_isolation_level(0)  # AUTOCOMMIT
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{db_name}" ENCODING \'UTF8\'')
        print(f"Создана база данных: {db_name}")
    cur.close()
    conn.close()

    os.environ["DB_NAME"] = db_name
    from database.init_db import init_db
    from database.seed import seed

    init_db()
    try:
        seed()
        print("Демо-данные загружены (seed).")
    except Exception as e:
        print(f"Seed пропущен (возможно, данные уже есть): {e}")
    print("База данных готова.")


if __name__ == "__main__":
    ensure_database()
