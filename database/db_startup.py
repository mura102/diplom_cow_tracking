"""Проверка PostgreSQL при старте приложения и настройка .env."""

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _save_env_password(password: str):
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
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(f"DB_PASSWORD={password}\n")
    if not out:
        out = [
            "DB_HOST=localhost\n",
            "DB_PORT=5432\n",
            "DB_NAME=cow_tracking_db\n",
            "DB_USER=postgres\n",
            f"DB_PASSWORD={password}\n",
        ]
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(out)
    os.environ["DB_PASSWORD"] = password


def _test_postgres_password(password: str) -> bool:
    import psycopg2

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=os.environ.get("DB_USER", "postgres"),
            password=password,
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "5432")),
        )
        conn.close()
        return True
    except Exception:
        return False


def _create_db_and_tables(password: str) -> str | None:
    """Возвращает текст ошибки или None при успехе."""
    import psycopg2

    db_name = os.environ.get("DB_NAME", "cow_tracking_db")
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=os.environ.get("DB_USER", "postgres"),
            password=password,
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "5432")),
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{db_name}" ENCODING \'UTF8\'')
        cur.close()
        conn.close()

        from database.init_db import init_db

        init_db()

        from database.seed import seed

        seed()
        return None
    except Exception as e:
        return str(e)


def ensure_db_or_prompt(parent=None) -> bool:
    """
    Проверяет подключение к PostgreSQL.
    При неверном пароле показывает диалог и сохраняет пароль в .env.
    """
    pwd = os.environ.get("DB_PASSWORD", "")
    if _test_postgres_password(pwd):
        err = _create_db_and_tables(pwd)
        return err is None

    from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

    for _ in range(3):
        text, ok = QInputDialog.getText(
            parent,
            "Подключение к PostgreSQL",
            "Введите пароль пользователя postgres\n"
            "(задаётся при установке PostgreSQL):",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not text.strip():
            return False
        pwd = text.strip()
        if not _test_postgres_password(pwd):
            QMessageBox.warning(
                parent,
                "Ошибка",
                "Неверный пароль или PostgreSQL не запущен.",
            )
            continue
        _save_env_password(pwd)
        err = _create_db_and_tables(pwd)
        if err:
            QMessageBox.critical(parent, "База данных", f"Ошибка настройки БД:\n{err}")
            return False
        QMessageBox.information(
            parent,
            "База данных",
            f"Подключение успешно.\nБаза: {os.environ.get('DB_NAME', 'cow_tracking_db')}",
        )
        return True

    return False
