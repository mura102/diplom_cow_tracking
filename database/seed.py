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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database.database import SessionLocal
from database.models import Diet, Cow, Employee, Section, Camera, Notification
from datetime import datetime


def seed():
    db = SessionLocal()
    try:
        # ── Рационы ──────────────────────────────────────────────────
        d1 = Diet(name="Standard",
                  composition_json={"hay": "10kg", "grain": "5kg"})
        d2 = Diet(name="Premium",
                  composition_json={"hay": "12kg", "grain": "7kg", "vitamins": "yes"})
        db.add_all([d1, d2])
        db.flush()

        # ── Секции ───────────────────────────────────────────────────
        s1 = Section(name="Section A", content_type="dairy")
        s2 = Section(name="Section B", content_type="beef")
        db.add_all([s1, s2])
        db.flush()

        # ── Камеры ───────────────────────────────────────────────────
        db.add_all([
            Camera(id_section=s1.id_section,
                   ip_address="192.168.1.10",
                   location="Section A - East",
                   resolution="1920x1080", fps=25, is_active=True),
            Camera(id_section=s2.id_section,
                   ip_address="192.168.1.11",
                   location="Section B - West",
                   resolution="1280x720", fps=15, is_active=True),
        ])

        # ── Коровы ───────────────────────────────────────────────────
        cows = [
            Cow(tag_number="A-01", breed="Holstein",
                weight_kg=580.0, status="healthy", id_diet=d1.id_diet, cow_number=1),
            Cow(tag_number="A-02", breed="Holstein",
                weight_kg=610.0, status="healthy", id_diet=d1.id_diet, cow_number=2),
            Cow(tag_number="B-01", breed="Simmental",
                weight_kg=540.0, status="pregnant", id_diet=d2.id_diet, cow_number=3),
            Cow(tag_number="B-02", breed="Simmental",
                weight_kg=520.0, status="healthy", id_diet=d2.id_diet, cow_number=4),
            Cow(tag_number="C-12", breed="Jersey",
                weight_kg=430.0, status="sick", id_diet=d1.id_diet, cow_number=5),
        ]
        db.add_all(cows)
        db.flush()

        # ── Сотрудники ───────────────────────────────────────────────
        emps = [
            Employee(full_name="Ivanov Ivan Ivanovich",
                     phone="+7-900-111-22-33", email="ivanov@farm.ru"),
            Employee(full_name="Petrova Anna Sergeevna",
                     phone="+7-900-444-55-66", email="petrova@farm.ru"),
            Employee(full_name="Sidorov Petr Alekseevich",
                     phone="+7-900-777-88-99", email="sidorov@farm.ru"),
        ]
        db.add_all(emps)
        db.flush()

        # ── Уведомления (вместо Event) ────────────────────────────────
        # cow_tag → ищем корову по tag_number и берём id_cow
        cow_c12 = next(c for c in cows if c.tag_number == "C-12")
        cow_a01 = next(c for c in cows if c.tag_number == "A-01")
        cow_b01 = next(c for c in cows if c.tag_number == "B-01")

        notifications = [
            Notification(
                id_cow=cow_c12.id_cow,
                alert_type="ACTIVITY",
                severity="WARNING",
                triggered_at=datetime.now(),
                message="Low activity detected",
            ),
            Notification(
                id_cow=cow_a01.id_cow,
                alert_type="FALL",
                severity="CRITICAL",
                triggered_at=datetime.now(),
                message="Animal fall detected",
            ),
            Notification(
                id_cow=cow_b01.id_cow,
                alert_type="FEED",
                severity="WARNING",
                triggered_at=datetime.now(),
                message="Feeding anomaly",
            ),
        ]
        db.add_all(notifications)

        db.commit()
        print("OK: seed data inserted successfully.")
    except Exception as e:
        db.rollback()
        print(f"SEED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
