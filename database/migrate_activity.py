"""Создаёт и мигрирует таблицы активности/сна (включая recognized_tag)."""

from sqlalchemy import inspect, text

from database.database import engine


def _column_exists(inspector, table_name, column_name):
    if not inspector.has_table(table_name):
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_activity_tables():
    from database.models import (
        ActivityCowResult,
        ActivityFrame,
        ActivitySession,
        SleepCowResult,
        SleepFrame,
        SleepSession,
    )

    inspector = inspect(engine)
    ActivitySession.__table__.create(bind=engine, checkfirst=True)
    ActivityFrame.__table__.create(bind=engine, checkfirst=True)
    SleepSession.__table__.create(bind=engine, checkfirst=True)
    SleepFrame.__table__.create(bind=engine, checkfirst=True)
    ActivityCowResult.__table__.create(bind=engine, checkfirst=True)
    SleepCowResult.__table__.create(bind=engine, checkfirst=True)

    migrations = []
    if inspector.has_table("sessions") and not _column_exists(
        inspector, "sessions", "recognized_tag"
    ):
        migrations.append(
            "ALTER TABLE sessions ADD COLUMN recognized_tag VARCHAR(20)"
        )
    if inspector.has_table("frames") and not _column_exists(
        inspector, "frames", "recognized_tag"
    ):
        migrations.append(
            "ALTER TABLE frames ADD COLUMN recognized_tag VARCHAR(20)"
        )
    if inspector.has_table("sleep_sessions") and not _column_exists(
        inspector, "sleep_sessions", "recognized_tag"
    ):
        migrations.append(
            "ALTER TABLE sleep_sessions ADD COLUMN recognized_tag VARCHAR(20)"
        )
    if inspector.has_table("sleep_frames") and not _column_exists(
        inspector, "sleep_frames", "recognized_tag"
    ):
        migrations.append(
            "ALTER TABLE sleep_frames ADD COLUMN recognized_tag VARCHAR(20)"
        )

    if migrations:
        with engine.begin() as conn:
            for ddl in migrations:
                conn.execute(text(ddl))
