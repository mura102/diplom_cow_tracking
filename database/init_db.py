# database/init_db.py
from database.database import Base, engine
import database.models  # noqa: F401
from database.migrate_bcs import migrate_bcs_schema
from database.migrate_activity import migrate_activity_tables


def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_bcs_schema()
    migrate_activity_tables()
    print("All tables created successfully")


if __name__ == "__main__":
    init_db()