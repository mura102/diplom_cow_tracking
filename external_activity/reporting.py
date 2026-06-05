"""
Формирование суточных отчётов и проверка аномалий.
Автор: Рената. Адаптирован для ERP "Рога и копыта".

Изменения по сравнению с оригиналом:
  1. Импорт db_config — из external_activity.db_config
"""

import datetime
from typing import Dict, List, Tuple

# ── импорт подключения к БД ───────────────────────────────────────────────────
from external_activity.db_config import get_connection, get_default_cow_number

THRESHOLDS = {
    'feed_min_minutes':     1,
    'feed_max_minutes':     3,
    'drink_min_minutes':    3,
    'drink_max_minutes':    4,
    'lying_min_minutes':    4,
    'standing_max_minutes': 1,
}


def get_daily_feed_drink_stats(cow_number, target_date: datetime.date) -> Dict[str, float]:
    conn = get_connection()
    cursor = conn.cursor()
    date_str = target_date.strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT total_duration_feed_sec, total_duration_drink_sec
        FROM sessions
        WHERE cow_number = %s AND start_time LIKE %s
    ''', (cow_number, date_str + '%'))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    total_feed_sec  = sum(row[0] for row in rows)
    total_drink_sec = sum(row[1] for row in rows)
    return {
        'feed_minutes':  total_feed_sec  / 60.0,
        'drink_minutes': total_drink_sec / 60.0
    }


def get_daily_sleep_stats(cow_number, target_date: datetime.date) -> Dict[str, float]:
    conn = get_connection()
    cursor = conn.cursor()
    date_str = target_date.strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT total_lying_sec, total_standing_sec
        FROM sleep_sessions
        WHERE cow_number = %s AND start_time LIKE %s
    ''', (cow_number, date_str + '%'))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    total_lying_sec    = sum(row[0] for row in rows)
    total_standing_sec = sum(row[1] for row in rows)
    return {
        'lying_minutes':    total_lying_sec    / 60.0,
        'standing_minutes': total_standing_sec / 60.0
    }


def check_anomalies(actual: Dict[str, float], thresholds: Dict[str, float]) -> List[str]:
    alerts = []
    feed = actual.get('feed_minutes', 0)
    if feed < thresholds['feed_min_minutes']:
        alerts.append(f"Питание слишком короткое: {feed:.1f} мин (норма: ≥{thresholds['feed_min_minutes']} мин)")
    elif feed > thresholds['feed_max_minutes']:
        alerts.append(f"Питание слишком долгое: {feed:.1f} мин (норма: ≤{thresholds['feed_max_minutes']} мин)")

    drink = actual.get('drink_minutes', 0)
    if drink < thresholds['drink_min_minutes']:
        alerts.append(f"Питьё слишком короткое: {drink:.1f} мин (норма: ≥{thresholds['drink_min_minutes']} мин)")
    elif drink > thresholds['drink_max_minutes']:
        alerts.append(f"Питьё слишком обильное: {drink:.1f} мин (норма: ≤{thresholds['drink_max_minutes']} мин)")

    lying = actual.get('lying_minutes', 0)
    if lying < thresholds['lying_min_minutes']:
        alerts.append(f"Недостаточный сон (лежание): {lying:.1f} мин (норма: ≥{thresholds['lying_min_minutes']} мин)")

    standing = actual.get('standing_minutes', 0)
    if standing > thresholds['standing_max_minutes']:
        alerts.append(f"Слишком много времени стояния в ночной период: {standing:.1f} мин (норма: ≤{thresholds['standing_max_minutes']} мин)")

    return alerts


def generate_daily_report(cow_number, target_date: datetime.date) -> Tuple[bool, List[str], Dict]:
    feed_drink_stats = get_daily_feed_drink_stats(cow_number, target_date)
    sleep_stats      = get_daily_sleep_stats(cow_number, target_date)
    all_stats        = {**feed_drink_stats, **sleep_stats}
    alerts           = check_anomalies(all_stats, THRESHOLDS)
    return (len(alerts) > 0, alerts, all_stats)


def save_daily_report(cow_number, target_date: datetime.date,
                      stats: Dict[str, float], alerts: List[str]):
    conn   = get_connection()
    cursor = conn.cursor()
    has_anomalies = len(alerts) > 0
    alerts_text   = "\n".join(alerts) if alerts else ""
    now           = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO daily_reports
            (cow_number, report_date, feed_minutes, drink_minutes,
             lying_minutes, standing_minutes, has_anomalies, alerts_text, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (cow_number, target_date,
           stats.get('feed_minutes'), stats.get('drink_minutes'),
           stats.get('lying_minutes'), stats.get('standing_minutes'),
           has_anomalies, alerts_text, now))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Отчёт сохранён в БД для коровы №{cow_number} за {target_date}")


def print_daily_summary(cow_number, target_date: datetime.date):
    has_anomalies, alerts, stats = generate_daily_report(cow_number, target_date)
    print(f"\n{'='*50}")
    print(f" ОТЧЁТ ЗА {target_date.strftime('%d.%m.%Y')} (корова №{cow_number})")
    print(f"{'='*50}")
    print(f" Питание:         {stats.get('feed_minutes', 0):.1f} мин")
    print(f" Питьё:           {stats.get('drink_minutes', 0):.1f} мин")
    print(f" Сон (лёжа):      {stats.get('lying_minutes', 0):.1f} мин")
    print(f" Стояние (ночью): {stats.get('standing_minutes', 0):.1f} мин")
    print(f"{'-'*50}")
    if has_anomalies:
        print("ОБНАРУЖЕНЫ АНОМАЛИИ:")
        for alert in alerts:
            print(f"  ⚠ {alert}")
    else:
        print("Все показатели в норме.")
    print(f"{'='*50}\n")
    save_daily_report(cow_number, target_date, stats, alerts)


if __name__ == "__main__":
    cow_number = get_default_cow_number()
    today      = datetime.date.today()
    print_daily_summary(cow_number, today)
