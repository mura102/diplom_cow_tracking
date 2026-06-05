# database/reports_db.py
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta


def get_connection(conn_params: dict):
    """Создаёт подключение к PostgreSQL."""
    return psycopg2.connect(**conn_params)


def fetch_notifications(conn_params: dict, days: int = 30) -> list[dict]:
    """
    Уведомления (events) за последние N дней.
    Используется для Excel-отчёта.
    """
    since_date = (datetime.now() - timedelta(days=days)).date()
    query = """
        SELECT
            e.id_event,
            e.cow_tag,
            e.message,
            e.level      AS severity,
            e.timestamp  AS created_at
        FROM events e
        WHERE DATE(e.timestamp) >= %s
        ORDER BY e.timestamp DESC
    """
    try:
        with get_connection(conn_params) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (since_date,))
                rows = [dict(row) for row in cur.fetchall()]
                print(f"[DEBUG] fetch_notifications rows={len(rows)}, since={since_date}")
                return rows
    except Exception as e:
        print(f"[reports_db] fetch_notifications error: {e}")
        return []


def fetch_activity_stats(conn_params: dict, days: int = 7) -> list[dict]:
    """
    Статистика активности по событиям:
      cow_tag, date, event_type(level), event_count.
    Используется для PDF-отчёта.
    """
    since_date = (datetime.now() - timedelta(days=days)).date()
    query = """
        SELECT
            e.cow_tag,
            DATE(e.timestamp)  AS date,
            e.level            AS event_type,
            COUNT(*)           AS event_count
        FROM events e
        WHERE DATE(e.timestamp) >= %s
        GROUP BY e.cow_tag, DATE(e.timestamp), e.level
        ORDER BY date DESC, e.cow_tag
    """
    try:
        with get_connection(conn_params) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (since_date,))
                rows = [dict(row) for row in cur.fetchall()]
                print(f"[DEBUG] fetch_activity_stats rows={len(rows)}, since={since_date}")
                if rows:
                    print("[DEBUG] sample activity row:", rows[0])
                return rows
    except Exception as e:
        print(f"[reports_db] fetch_activity_stats error: {e}")
        return []


def fetch_cow_summary(conn_params: dict) -> list[dict]:
    """
    Сводка по коровам:
      tag_number, breed, weight_kg, status, last_inspection, total_events.
    """
    query = """
        SELECT
            c.tag_number,
            c.breed,
            c.weight_kg,
            c.status,
            c.last_inspection,
            COUNT(DISTINCT e.id_event) AS total_events
        FROM cows c
        LEFT JOIN events e ON e.cow_tag = c.tag_number
        GROUP BY c.id_cow, c.tag_number, c.breed,
                 c.weight_kg, c.status, c.last_inspection
        ORDER BY c.tag_number
    """
    try:
        with get_connection(conn_params) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                rows = [dict(row) for row in cur.fetchall()]
                print(f"[DEBUG] fetch_cow_summary rows={len(rows)}")
                if rows:
                    print("[DEBUG] sample cow row:", rows[0])
                return rows
    except Exception as e:
        print(f"[reports_db] fetch_cow_summary error: {e}")
        return []