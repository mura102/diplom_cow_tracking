import psycopg2

DB_NAME = "cow_tracking_db"          # ваша существующая БД
DB_USER = "postgres"
DB_PASSWORD = ""   # замените
DB_HOST = "localhost"
DB_PORT = "5432"

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# Просто возвращаем фиксированный номер коровы
def get_default_cow_number():
    return 1
