from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Единственный Base — импортируем из database.py
from database.database import Base


# ---------- Секции ----------

class Section(Base):
    __tablename__ = "sections"

    id_section   = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String(50), nullable=False)
    content_type = Column(String(30), nullable=False)

    cameras = relationship("Camera", back_populates="section")


# ---------- Камеры и видеопотоки ----------

class Camera(Base):
    __tablename__ = "cameras"

    id_camera  = Column(Integer, primary_key=True, autoincrement=True)
    id_section = Column(Integer, ForeignKey("sections.id_section"))
    ip_address = Column(String(45))
    location   = Column(String(100))
    resolution = Column(String(20))
    fps        = Column(Integer)
    is_active  = Column(Boolean, default=True)

    section = relationship("Section", back_populates="cameras")
    streams = relationship("VideoStream", back_populates="camera")


class VideoStream(Base):
    __tablename__ = "video_streams"

    id_stream  = Column(BigInteger, primary_key=True, autoincrement=True)
    id_camera  = Column(Integer, ForeignKey("cameras.id_camera"))
    location   = Column(String(100))
    start_time = Column(DateTime)
    end_time   = Column(DateTime)
    file_path  = Column(String(500))

    camera        = relationship("Camera", back_populates="streams")
    ai_activities = relationship("AIActivity", back_populates="stream")
    bcs_sessions  = relationship("BCSSession", back_populates="stream")


# ---------- Коровы и рационы ----------

class Diet(Base):
    __tablename__ = "diets"

    id_diet          = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(100), nullable=False)
    composition_json = Column(JSON)

    cows     = relationship("Cow", back_populates="diet")
    feedings = relationship("FeedingJournal", back_populates="diet")


class Cow(Base):
    __tablename__ = "cows"

    id_cow          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tag_number      = Column(String(20), nullable=False, unique=True)
    breed           = Column(String(100))
    weight_kg       = Column(Float)
    status          = Column(String(50))
    id_diet         = Column(Integer, ForeignKey("diets.id_diet"))
    last_inspection = Column(DateTime)
    cow_number      = Column(Integer, unique=True)

    diet            = relationship("Diet", back_populates="cows")
    ai_activities   = relationship("AIActivity", back_populates="cow")
    notifications   = relationship("Notification", back_populates="cow")
    feedings        = relationship("FeedingJournal", back_populates="cow")
    medical_records = relationship("MedicalRecord", back_populates="cow")
    assignments     = relationship("Assignment", back_populates="cow")
    bcs_sessions    = relationship("BCSSession", back_populates="cow")
    bcs_measurements = relationship("BCSMeasurement", back_populates="cow")


# ---------- Сотрудники и назначения ----------

class Employee(Base):
    __tablename__ = "employees"

    id_employee = Column(Integer, primary_key=True, autoincrement=True)
    full_name   = Column(String(150), nullable=False)
    phone       = Column(String(20))
    email       = Column(String(100))

    assignments            = relationship("Assignment", back_populates="employee")
    feedings               = relationship("FeedingJournal", back_populates="employee")
    medical_records        = relationship("MedicalRecord", back_populates="vet")
    notifications_resolved = relationship(
        "Notification", back_populates="resolved_by_employee"
    )


class Assignment(Base):
    __tablename__ = "assignments"

    cow_id      = Column(UUID(as_uuid=True), ForeignKey("cows.id_cow"), primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id_employee"), primary_key=True)

    cow      = relationship("Cow", back_populates="assignments")
    employee = relationship("Employee", back_populates="assignments")


# ---------- Журнал кормления ----------

class FeedingJournal(Base):
    __tablename__ = "feeding_journal"

    id_feeding  = Column(BigInteger, primary_key=True, autoincrement=True)
    id_cow      = Column(UUID(as_uuid=True), ForeignKey("cows.id_cow"), nullable=False)
    id_diet     = Column(Integer, ForeignKey("diets.id_diet"))
    id_employee = Column(Integer, ForeignKey("employees.id_employee"))
    issued_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    weight_kg   = Column(Float)

    cow      = relationship("Cow", back_populates="feedings")
    diet     = relationship("Diet", back_populates="feedings")
    employee = relationship("Employee", back_populates="feedings")


# ---------- Медицинские записи ----------

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id_record       = Column(BigInteger, primary_key=True, autoincrement=True)
    id_cow          = Column(UUID(as_uuid=True), ForeignKey("cows.id_cow"), nullable=False)
    id_vet          = Column(Integer, ForeignKey("employees.id_employee"))
    diagnosis       = Column(String)
    inspection_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    cow = relationship("Cow", back_populates="medical_records")
    vet = relationship("Employee", back_populates="medical_records")


# ---------- Активности ИИ и уведомления ----------

class AIActivity(Base):
    __tablename__ = "ai_activities"

    id_log        = Column(BigInteger, primary_key=True, autoincrement=True)
    id_cow        = Column(UUID(as_uuid=True), ForeignKey("cows.id_cow"), nullable=False)
    id_stream     = Column(BigInteger, ForeignKey("video_streams.id_stream"))
    activity_type = Column(String(50), nullable=False)  # FEED/DRINK/SLEEP/FALL/BCS/...
    start_time    = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time      = Column(DateTime)
    confidence    = Column(Float)
    extra_json    = Column(JSON)

    cow           = relationship("Cow", back_populates="ai_activities")
    stream        = relationship("VideoStream", back_populates="ai_activities")
    notifications = relationship("Notification", back_populates="log")


class Notification(Base):
    __tablename__ = "notifications"

    id_notification = Column(BigInteger, primary_key=True, autoincrement=True)
    id_cow          = Column(UUID(as_uuid=True), ForeignKey("cows.id_cow"))
    id_log          = Column(BigInteger, ForeignKey("ai_activities.id_log"))
    alert_type      = Column(String(50))
    severity        = Column(String(20))  # INFO/WARNING/CRITICAL
    triggered_at    = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at     = Column(DateTime)
    resolved_by     = Column(Integer, ForeignKey("employees.id_employee"))
    message         = Column(String)

    cow                    = relationship("Cow", back_populates="notifications")
    log                    = relationship("AIActivity", back_populates="notifications")
    resolved_by_employee   = relationship(
        "Employee", back_populates="notifications_resolved"
    )


# ---------- БКС: сессии и измерения ----------

class BCSSession(Base):
    __tablename__ = "bcs_sessions"

    id                 = Column(BigInteger, primary_key=True, autoincrement=True)
    id_cow             = Column(UUID(as_uuid=True), ForeignKey("cows.id_cow"), nullable=True)
    id_stream          = Column(BigInteger, ForeignKey("video_streams.id_stream"), nullable=True)
    start_time         = Column(DateTime, nullable=False, default=datetime.utcnow)
    image_path         = Column(String(500), nullable=False, default="")
    video_path         = Column(String(500), nullable=True)
    source_type        = Column(String(20), nullable=False, default="image")
    num_cows_detected  = Column(Integer, nullable=False)

    cow          = relationship("Cow", back_populates="bcs_sessions")
    stream       = relationship("VideoStream", back_populates="bcs_sessions")
    measurements = relationship("BCSMeasurement", back_populates="session")


class BCSMeasurement(Base):
    __tablename__ = "bcs_measurements"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    id_session      = Column(BigInteger, ForeignKey("bcs_sessions.id"), nullable=False)
    id_cow          = Column(UUID(as_uuid=True), ForeignKey("cows.id_cow"), nullable=True)
    recognized_tag  = Column(String(20), nullable=True)
    cow_number      = Column(Integer, nullable=True)
    bcs_value       = Column(Float, nullable=False)
    confidence      = Column(Float)
    bbox_coords     = Column(String)
    frame_number    = Column(Integer, nullable=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("BCSSession", back_populates="measurements")
    cow     = relationship("Cow", back_populates="bcs_measurements")

# ---------- Активность: кормление / питьё ----------

class ActivitySession(Base):
    __tablename__ = "sessions"

    id                         = Column(Integer, primary_key=True, autoincrement=True)
    cow_number                 = Column(Integer, ForeignKey("cows.cow_number"), nullable=False)
    recognized_tag             = Column(String(20), nullable=True)
    start_time                 = Column(String, nullable=False)
    total_duration_feed_sec    = Column(Float, nullable=False, default=0.0)
    total_duration_drink_sec   = Column(Float, nullable=False, default=0.0)
    num_frames                 = Column(Integer, nullable=False, default=0)

    frames = relationship(
        "ActivityFrame", back_populates="session", cascade="all, delete-orphan"
    )


class ActivityFrame(Base):
    __tablename__ = "frames"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    session_id       = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp_sec    = Column(Float, nullable=False)
    cow_detected     = Column(Boolean, nullable=False, default=False)
    state            = Column(String(50))
    camera_location  = Column(String(100))
    image_path       = Column(String(500))
    confidence       = Column(Float)
    recognized_tag   = Column(String(20), nullable=True)

    session = relationship("ActivitySession", back_populates="frames")


class ActivityCowResult(Base):
    __tablename__ = "activity_cow_results"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    session_id     = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    recognized_tag = Column(String(20), nullable=False)
    cow_number     = Column(Integer, ForeignKey("cows.cow_number"), nullable=True)
    feed_sec       = Column(Float, nullable=False, default=0.0)
    drink_sec      = Column(Float, nullable=False, default=0.0)


# ---------- Сон (Рената) ----------

class SleepSession(Base):
    __tablename__ = "sleep_sessions"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    cow_number         = Column(Integer, ForeignKey("cows.cow_number"), nullable=False)
    recognized_tag     = Column(String(20), nullable=True)
    start_time         = Column(String, nullable=False)
    night_start        = Column(String)
    night_end          = Column(String)
    total_lying_sec    = Column(Float, nullable=False, default=0.0)
    total_standing_sec = Column(Float, nullable=False, default=0.0)
    num_frames         = Column(Integer, nullable=False, default=0)

    frames = relationship("SleepFrame", back_populates="session", cascade="all, delete-orphan")


class SleepFrame(Base):
    __tablename__ = "sleep_frames"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    session_id    = Column(Integer, ForeignKey("sleep_sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp_sec = Column(Float, nullable=False)
    datetime_iso  = Column(String)
    posture         = Column(String)
    image_path      = Column(String)
    recognized_tag  = Column(String(20), nullable=True)

    session = relationship("SleepSession", back_populates="frames")


class SleepCowResult(Base):
    __tablename__ = "sleep_cow_results"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    session_id     = Column(Integer, ForeignKey("sleep_sessions.id", ondelete="CASCADE"), nullable=False)
    recognized_tag = Column(String(20), nullable=False)
    cow_number     = Column(Integer, ForeignKey("cows.cow_number"), nullable=True)
    lying_sec      = Column(Float, nullable=False, default=0.0)
    standing_sec   = Column(Float, nullable=False, default=0.0)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    cow_number       = Column(Integer, ForeignKey("cows.cow_number"), nullable=False)
    report_date      = Column(Date, nullable=False)
    feed_minutes     = Column(Float)
    drink_minutes    = Column(Float)
    lying_minutes    = Column(Float)
    standing_minutes = Column(Float)
    has_anomalies    = Column(Boolean, default=False)
    alerts_text      = Column(String)
    created_at       = Column(DateTime, default=datetime.utcnow)