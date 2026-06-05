# database/init_db.py
from database.database import Base, engine
import database.models  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully")


if __name__ == "__main__":
    init_db()