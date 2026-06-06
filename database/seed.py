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
from database.models import Diet, Cow, Employee, Section, Camera, Notification
from datetime import datetime

SEED_TAG_NUMBERS = ("A-01", "A-02", "B-01", "B-02", "C-12")


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


def seed():
    db = SessionLocal()
    try:
        if _seed_already_applied(db):
            print("OK: демо-данные уже есть, seed пропущен.")
            return

        d1 = _get_or_create_diet(
            db, "Standard", {"hay": "10kg", "grain": "5kg"}
        )
        d2 = _get_or_create_diet(
            db, "Premium", {"hay": "12kg", "grain": "7kg", "vitamins": "yes"}
        )

        s1 = _get_or_create_section(db, "Section A", "dairy")
        s2 = _get_or_create_section(db, "Section B", "beef")

        if not db.query(Camera).filter(Camera.ip_address == "192.168.1.10").first():
            db.add_all([
                Camera(
                    id_section=s1.id_section,
                    ip_address="192.168.1.10",
                    location=" Кормовая зона — Section A",
                    resolution="1920x1080",
                    fps=25,
                    is_active=True,
                ),
                Camera(
                    id_section=s2.id_section,
                    ip_address="192.168.1.11",
                    location="Питьевая зона — Section B",
                    resolution="1280x720",
                    fps=15,
                    is_active=True,
                ),
            ])

        cows = [
            _get_or_create_cow(
                db,
                "A-01",
                breed="Holstein",
                weight_kg=580.0,
                status="healthy",
                id_diet=d1.id_diet,
                cow_number=1,
            ),
            _get_or_create_cow(
                db,
                "A-02",
                breed="Holstein",
                weight_kg=610.0,
                status="healthy",
                id_diet=d1.id_diet,
                cow_number=2,
            ),
            _get_or_create_cow(
                db,
                "B-01",
                breed="Simmental",
                weight_kg=540.0,
                status="pregnant",
                id_diet=d2.id_diet,
                cow_number=3,
            ),
            _get_or_create_cow(
                db,
                "B-02",
                breed="Simmental",
                weight_kg=520.0,
                status="healthy",
                id_diet=d2.id_diet,
                cow_number=4,
            ),
            _get_or_create_cow(
                db,
                "C-12",
                breed="Jersey",
                weight_kg=430.0,
                status="sick",
                id_diet=d1.id_diet,
                cow_number=5,
            ),
        ]

        _get_or_create_employee(
            db,
            "ivanov@farm.ru",
            full_name="Ivanov Ivan Ivanovich",
            phone="+7-900-111-22-33",
        )
        _get_or_create_employee(
            db,
            "petrova@farm.ru",
            full_name="Petrova Anna Sergeevna",
            phone="+7-900-444-55-66",
        )
        _get_or_create_employee(
            db,
            "sidorov@farm.ru",
            full_name="Sidorov Petr Alekseevich",
            phone="+7-900-777-88-99",
        )

        cow_c12 = next(c for c in cows if c.tag_number == "C-12")
        cow_a01 = next(c for c in cows if c.tag_number == "A-01")
        cow_b01 = next(c for c in cows if c.tag_number == "B-01")

        seed_messages = [
            (cow_c12.id_cow, "ACTIVITY", "WARNING", "Low activity detected"),
            (cow_a01.id_cow, "FALL", "CRITICAL", "Animal fall detected"),
            (cow_b01.id_cow, "FEED", "WARNING", "Feeding anomaly"),
        ]
        for id_cow, alert_type, severity, message in seed_messages:
            exists = (
                db.query(Notification)
                .filter(
                    Notification.id_cow == id_cow,
                    Notification.message == message,
                )
                .first()
            )
            if not exists:
                db.add(
                    Notification(
                        id_cow=id_cow,
                        alert_type=alert_type,
                        severity=severity,
                        triggered_at=datetime.now(),
                        message=message,
                    )
                )

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
