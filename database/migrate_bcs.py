"""Миграция схемы BCS: добавляет колонки для распознавания ID и обработки видео."""

from sqlalchemy import inspect, text

from database.database import engine


def _column_exists(inspector, table_name, column_name):
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_bcs_schema():
    """Добавляет новые колонки в bcs_sessions и bcs_measurements, если их ещё нет."""
    inspector = inspect(engine)
    if not inspector.has_table("bcs_sessions"):
        return

    migrations = []

    if not _column_exists(inspector, "bcs_sessions", "video_path"):
        migrations.append(
            "ALTER TABLE bcs_sessions ADD COLUMN video_path VARCHAR(500)"
        )
    if not _column_exists(inspector, "bcs_sessions", "source_type"):
        migrations.append(
            "ALTER TABLE bcs_sessions ADD COLUMN source_type VARCHAR(20) DEFAULT 'image'"
        )

    if inspector.has_table("bcs_measurements"):
        if not _column_exists(inspector, "bcs_measurements", "recognized_tag"):
            migrations.append(
                "ALTER TABLE bcs_measurements ADD COLUMN recognized_tag VARCHAR(20)"
            )
        if not _column_exists(inspector, "bcs_measurements", "cow_number"):
            migrations.append(
                "ALTER TABLE bcs_measurements ADD COLUMN cow_number INTEGER"
            )
        if not _column_exists(inspector, "bcs_measurements", "frame_number"):
            migrations.append(
                "ALTER TABLE bcs_measurements ADD COLUMN frame_number INTEGER"
            )

    if not migrations:
        return

    with engine.begin() as conn:
        for ddl in migrations:
            conn.execute(text(ddl))
