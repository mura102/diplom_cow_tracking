from external_activity.db_config import get_connection
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [r[0] for r in cur.fetchall()]
print("Таблицы в БД:", tables)
conn.close()
