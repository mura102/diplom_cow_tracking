import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == "database":
    project_root = os.path.dirname(current_dir)
    if current_dir in sys.path:
        sys.path.remove(current_dir)
else:
    project_root = current_dir
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _load_dotenv():
    env_path = os.path.join(project_root, ".env")
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database.database import SessionLocal
from database.models import (
    Diet, Cow, Employee, Section, Camera, Notification, AIActivity,
    ActivitySession, SleepSession,
)
from datetime import datetime, timedelta
import datetime as dt

SEED_TAG_NUMBERS = (
    "А-01", "А-02", "А-03", "А-04", "А-05",
    "Б-01", "Б-02", "Б-03",
    "В-01", "В-02",
)


def _seed_already_applied(db) -> bool:
    return (
        db.query(Cow)
        .filter(Cow.tag_number.in_(SEED_TAG_NUMBERS))
        .count() >= len(SEED_TAG_NUMBERS)
    )


def _get_or_create_diet(db, name, composition_json):
    diet = db.query(Diet).filter(Diet.name == name).first()
    if diet:
        return diet
    diet = Diet(name=name, composition_json=composition_json)
    db.add(diet)
    db.flush()
    return diet


def _get_or_create_section(db, name, content_type):
    section = db.query(Section).filter(Section.name == name).first()
    if section:
        return section
    section = Section(name=name, content_type=content_type)
    db.add(section)
    db.flush()
    return section


def _get_or_create_cow(db, tag_number, **kwargs):
    cow = db.query(Cow).filter(Cow.tag_number == tag_number).first()
    if cow:
        return cow
    cow = Cow(tag_number=tag_number, **kwargs)
    db.add(cow)
    db.flush()
    return cow


def _get_or_create_employee(db, email, **kwargs):
    emp = db.query(Employee).filter(Employee.email == email).first()
    if emp:
        return emp
    emp = Employee(email=email, **kwargs)
    db.add(emp)
    db.flush()
    return emp


def _seed_daily_report_demo(db):
    """
    ВРЕМЕННО: данные для демонстрации суточного отчёта (reporting.py).
    Чтобы откатить — удали вызов _seed_daily_report_demo(db) в конце seed().
    """
    today_str = dt.date.today().strftime("%Y-%m-%d")
    demo_cow_number = 1  # А-01

    if not db.query(ActivitySession).filter(
        ActivitySession.cow_number == demo_cow_number,
        ActivitySession.start_time.like(f"{today_str}%")
    ).first():
        db.add(ActivitySession(
            cow_number=demo_cow_number,
            recognized_tag="А-01",
            start_time=f"{today_str} 09:00:00",
            total_duration_feed_sec=30,
            total_duration_drink_sec=600,
            num_frames=10,
        ))

    if not db.query(SleepSession).filter(
        SleepSession.cow_number == demo_cow_number,
        SleepSession.start_time.like(f"{today_str}%")
    ).first():
        db.add(SleepSession(
            cow_number=demo_cow_number,
            recognized_tag="А-01",
            start_time=f"{today_str} 22:00:00",
            night_start="22:00",
            night_end="05:00",
            total_lying_sec=120,
            total_standing_sec=90,
            num_frames=5,
        ))

    print("OK: demo-данные для суточного отчёта добавлены.")


def _seed_notifications(db, cow_map):
    """
    Уведомления добавляются ВСЕГДА при каждом запуске seed.py.
    Привязаны только к существующим коровам (cow_number от 1 до 10).

    Дедупликация — по паре (id_cow, message), без учёта triggered_at,
    чтобы повторные запуски seed.py НЕ плодили дубликаты с новым временем.
    """
    today = dt.date.today()
    base_time = datetime.combine(today, dt.time(0, 0))

    notifications_data = [
        (cow_map["В-01"].id_cow, "FEED",  "WARNING",  base_time + timedelta(hours=6)),
        (cow_map["А-02"].id_cow, "DRINK", "WARNING",  base_time + timedelta(hours=10)),
        (cow_map["А-03"].id_cow, "FEED",  "WARNING",  base_time + timedelta(hours=14)),
        (cow_map["Б-02"].id_cow, "DRINK", "CRITICAL", base_time + timedelta(hours=16)),
        (cow_map["А-01"].id_cow, "FEED",  "WARNING",  base_time + timedelta(hours=19)),
        (cow_map["В-02"].id_cow, "DRINK", "WARNING",  base_time + timedelta(hours=21)),
        (cow_map["Б-03"].id_cow, "FEED",  "CRITICAL", base_time + timedelta(hours=23)),
    ]

    MESSAGE_MAP = {
        ("FEED", "WARNING"):   "Низкая продолжительность питания.",
        ("FEED", "CRITICAL"):  "Отказ от корма в течение длительного времени.",
        ("DRINK", "WARNING"):  "Низкая продолжительность водопоя.",
        ("DRINK", "CRITICAL"): "Отказ от воды в течение длительного времени.",
    }

    for id_cow, alert_type, severity, triggered_at in notifications_data:
        message = MESSAGE_MAP.get((alert_type, severity), "Зафиксировано отклонение.")

        exists = (
            db.query(Notification)
            .filter(
                Notification.id_cow == id_cow,
                Notification.message == message,
            )
            .first()
        )
        if not exists:
            db.add(Notification(
                id_cow=id_cow,
                alert_type=alert_type,
                severity=severity,
                triggered_at=triggered_at,
                message=message,
            ))
    print("OK: уведомления добавлены/обновлены.")


def seed():
    db = SessionLocal()
    try:
        if _seed_already_applied(db):
            print("OK: демо-данные уже есть, основной seed пропущен.")
        else:
            # ── Рационы кормления ──
            d_standard = _get_or_create_diet(
                db, "Стандартный (молочный)",
                {"сено": "12 кг", "комбикорм": "6 кг", "силос": "15 кг", "вода": "80 л"}
            )
            d_premium = _get_or_create_diet(
                db, "Усиленный (высокопродуктивный)",
                {"сено": "14 кг", "комбикорм": "9 кг", "силос": "18 кг", "витамины": "да", "вода": "100 л"}
            )
            d_pregnant = _get_or_create_diet(
                db, "Для стельных коров",
                {"сено": "10 кг", "комбикорм": "4 кг", "силос": "12 кг", "минералы": "да", "вода": "70 л"}
            )

            # ── Секции предприятия ──
            s1 = _get_or_create_section(db, "Корпус А — молочное стадо", "молочное")
            s2 = _get_or_create_section(db, "Корпус Б — мясное стадо", "мясное")
            s3 = _get_or_create_section(db, "Корпус В — карантин", "карантин")

            # ── Камеры видеонаблюдения ──
            cameras_data = [
                ("192.168.1.10", "Кормовая зона — Корпус А", "1920x1080", 25, s1),
                ("192.168.1.11", "Зона отдыха — Корпус А", "1920x1080", 25, s1),
                ("192.168.1.20", "Кормовая зона — Корпус Б", "1280x720", 20, s2),
                ("192.168.1.21", "Поилки — Корпус Б", "1280x720", 20, s2),
                ("192.168.1.30", "Карантинный бокс — Корпус В", "1920x1080", 15, s3),
            ]
            for ip, loc, res, fps, section in cameras_data:
                if not db.query(Camera).filter(Camera.ip_address == ip).first():
                    db.add(Camera(
                        id_section=section.id_section,
                        ip_address=ip,
                        location=loc,
                        resolution=res,
                        fps=fps,
                        is_active=True,
                    ))

            # ── Животные (cow_number строго от 1 до 10) ──
            now = datetime.now()
            cows = [
                _get_or_create_cow(db, "А-01", breed="Голштинская", weight_kg=585.0,
                                   status="здорова", id_diet=d_standard.id_diet,
                                   cow_number=1, last_inspection=now - timedelta(days=3)),
                _get_or_create_cow(db, "А-02", breed="Голштинская", weight_kg=612.0,
                                   status="здорова", id_diet=d_premium.id_diet,
                                   cow_number=2, last_inspection=now - timedelta(days=1)),
                _get_or_create_cow(db, "А-03", breed="Голштинская", weight_kg=548.0,
                                   status="стельная", id_diet=d_pregnant.id_diet,
                                   cow_number=3, last_inspection=now - timedelta(days=5)),
                _get_or_create_cow(db, "А-04", breed="Голштинская", weight_kg=590.0,
                                   status="здорова", id_diet=d_standard.id_diet,
                                   cow_number=4, last_inspection=now - timedelta(days=2)),
                _get_or_create_cow(db, "А-05", breed="Голштинская", weight_kg=575.0,
                                   status="здорова", id_diet=d_premium.id_diet,
                                   cow_number=5, last_inspection=now - timedelta(days=7)),
                _get_or_create_cow(db, "Б-01", breed="Симментальская", weight_kg=540.0,
                                   status="здорова", id_diet=d_standard.id_diet,
                                   cow_number=6, last_inspection=now - timedelta(days=4)),
                _get_or_create_cow(db, "Б-02", breed="Симментальская", weight_kg=520.0,
                                   status="стельная", id_diet=d_pregnant.id_diet,
                                   cow_number=7, last_inspection=now - timedelta(days=2)),
                _get_or_create_cow(db, "Б-03", breed="Симментальская", weight_kg=555.0,
                                   status="здорова", id_diet=d_standard.id_diet,
                                   cow_number=8, last_inspection=now - timedelta(days=6)),
                _get_or_create_cow(db, "В-01", breed="Джерсейская", weight_kg=430.0,
                                   status="на лечении", id_diet=d_standard.id_diet,
                                   cow_number=9, last_inspection=now - timedelta(hours=12)),
                _get_or_create_cow(db, "В-02", breed="Джерсейская", weight_kg=445.0,
                                   status="на карантине", id_diet=d_standard.id_diet,
                                   cow_number=10, last_inspection=now - timedelta(hours=6)),
            ]

            # ── Сотрудники ──
            _get_or_create_employee(
                db, "khasanova@agroferm.ru",
                full_name="Хасанова Алия Рустамовна",
                phone="+7-917-234-56-78",
            )
            _get_or_create_employee(
                db, "petrov@agroferm.ru",
                full_name="Петров Дмитрий Сергеевич",
                phone="+7-917-345-67-89",
            )
            _get_or_create_employee(
                db, "smirnova@agroferm.ru",
                full_name="Смирнова Екатерина Андреевна",
                phone="+7-917-456-78-90",
            )
            _get_or_create_employee(
                db, "gafar@agroferm.ru",
                full_name="Гафаров Мурат Радикович",
                phone="+7-917-567-89-01",
            )
            _get_or_create_employee(
                db, "vasilev@agroferm.ru",
                full_name="Васильев Олег Николаевич",
                phone="+7-917-678-90-12",
            )

            # ── Активности ИИ (для детальной статистики в отчётах) ──
            cow_map = {c.tag_number: c for c in cows}

            activities_data = [
                (cow_map["А-01"].id_cow, "FEED",  now - timedelta(hours=20), now - timedelta(hours=19, minutes=40), 0.92),
                (cow_map["А-01"].id_cow, "DRINK", now - timedelta(hours=18), now - timedelta(hours=17, minutes=55), 0.88),
                (cow_map["А-01"].id_cow, "SLEEP", now - timedelta(hours=14), now - timedelta(hours=8), 0.95),
                (cow_map["А-01"].id_cow, "FEED",  now - timedelta(hours=4),  now - timedelta(hours=3, minutes=25), 0.91),
                (cow_map["А-02"].id_cow, "FEED",  now - timedelta(hours=22), now - timedelta(hours=21, minutes=30), 0.91),
                (cow_map["А-02"].id_cow, "FEED",  now - timedelta(hours=10), now - timedelta(hours=9, minutes=20), 0.89),
                (cow_map["А-02"].id_cow, "DRINK", now - timedelta(hours=15), now - timedelta(hours=14, minutes=50), 0.93),
                (cow_map["А-03"].id_cow, "SLEEP", now - timedelta(hours=16), now - timedelta(hours=4), 0.96),
                (cow_map["А-03"].id_cow, "FEED",  now - timedelta(hours=22), now - timedelta(hours=21, minutes=45), 0.84),
                (cow_map["А-04"].id_cow, "FEED",  now - timedelta(hours=21), now - timedelta(hours=20, minutes=25), 0.90),
                (cow_map["А-04"].id_cow, "DRINK", now - timedelta(hours=12), now - timedelta(hours=11, minutes=45), 0.87),
                (cow_map["А-04"].id_cow, "FEED",  now - timedelta(hours=6),  now - timedelta(hours=5, minutes=30), 0.94),
                (cow_map["А-04"].id_cow, "DRINK", now - timedelta(hours=2),  now - timedelta(hours=1, minutes=50), 0.90),
                (cow_map["А-05"].id_cow, "FEED",  now - timedelta(hours=19), now - timedelta(hours=18, minutes=35), 0.91),
                (cow_map["А-05"].id_cow, "SLEEP", now - timedelta(hours=13), now - timedelta(hours=2), 0.97),
                (cow_map["Б-01"].id_cow, "FEED",  now - timedelta(hours=23), now - timedelta(hours=22, minutes=20), 0.88),
                (cow_map["Б-01"].id_cow, "DRINK", now - timedelta(hours=17), now - timedelta(hours=16, minutes=50), 0.90),
                (cow_map["Б-01"].id_cow, "FEED",  now - timedelta(hours=7),  now - timedelta(hours=6, minutes=15), 0.92),
                (cow_map["Б-02"].id_cow, "FEED",  now - timedelta(hours=20), now - timedelta(hours=19, minutes=15), 0.86),
                (cow_map["Б-02"].id_cow, "SLEEP", now - timedelta(hours=15), now - timedelta(hours=5), 0.93),
                (cow_map["Б-03"].id_cow, "SLEEP", now - timedelta(hours=24), now - timedelta(hours=1), 0.94),
                (cow_map["Б-03"].id_cow, "DRINK", now - timedelta(hours=25), now - timedelta(hours=24, minutes=45), 0.85),
                (cow_map["В-01"].id_cow, "FEED",  now - timedelta(hours=48), now - timedelta(hours=47, minutes=30), 0.82),
                (cow_map["В-01"].id_cow, "SLEEP", now - timedelta(hours=40), now - timedelta(hours=20), 0.91),
                (cow_map["В-02"].id_cow, "DRINK", now - timedelta(hours=36), now - timedelta(hours=35, minutes=45), 0.85),
                (cow_map["В-02"].id_cow, "FEED",  now - timedelta(hours=30), now - timedelta(hours=29, minutes=20), 0.83),
                (cow_map["В-02"].id_cow, "SLEEP", now - timedelta(hours=28), now - timedelta(hours=16), 0.90),
            ]

            for id_cow, activity_type, start, end, conf in activities_data:
                exists = (
                    db.query(AIActivity)
                    .filter(AIActivity.id_cow == id_cow, AIActivity.start_time == start)
                    .first()
                )
                if not exists:
                    db.add(AIActivity(
                        id_cow=id_cow,
                        id_stream=None,
                        activity_type=activity_type,
                        start_time=start,
                        end_time=end,
                        confidence=conf,
                    ))

            print("OK: демо-данные успешно загружены.")

        # ── Уведомления добавляются ВСЕГДА, даже если основной seed был пропущен ──
        cow_map_all = {c.tag_number: c for c in db.query(Cow).all()}
        _seed_notifications(db, cow_map_all)

        # ── ВРЕМЕННО: данные для демонстрации суточного отчёта ──
        # Чтобы откатить — удали эту строку.
        _seed_daily_report_demo(db)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"SEED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()