# database/reports_db.py
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta


def get_connection(conn_params: dict):
    """Создаёт подключение к PostgreSQL."""
    return psycopg2.connect(**conn_params)


def fetch_notifications(conn_params: dict, days: int = 30) -> list[dict]:
    """
    Уведомления за последние N дней.
    Используется для Excel-отчёта.
    """
    since_date = (datetime.now() - timedelta(days=days)).date()
    query = """
        SELECT
            n.id_notification,
            c.cow_number    AS cow_tag,
            n.message,
            n.severity,
            n.triggered_at  AS created_at
        FROM notifications n
        LEFT JOIN cows c ON c.id_cow = n.id_cow
        WHERE DATE(n.triggered_at) >= %s
        ORDER BY n.triggered_at DESC
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
    since_date = (datetime.now() - timedelta(days=days)).date()
    query = """
        SELECT
            c.cow_number        AS cow_tag,
            DATE(a.start_time)  AS date,
            a.activity_type     AS event_type,
            COUNT(*)            AS event_count
        FROM ai_activities a
        JOIN cows c ON c.id_cow = a.id_cow
        WHERE DATE(a.start_time) >= %s
        GROUP BY c.cow_number, DATE(a.start_time), a.activity_type
        ORDER BY date DESC, c.cow_number
    """
    try:
        with get_connection(conn_params) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (since_date,))
                rows = [dict(row) for row in cur.fetchall()]
                print(f"[DEBUG] fetch_activity_stats rows={len(rows)}, since={since_date}")
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
            c.cow_number,
            c.tag_number,
            c.breed,
            c.weight_kg,
            c.status,
            c.last_inspection,
            COUNT(DISTINCT a.id_log) AS total_events
        FROM cows c
        LEFT JOIN ai_activities a ON a.id_cow = c.id_cow
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
                return rows
    except Exception as e:
        print(f"[reports_db] fetch_cow_summary error: {e}")
        return []