from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db import Base

class LicenseSnapshot(Base):
    __tablename__ = "license_snapshots"

    id = Column(Integer, primary_key=True)
    captured_at_utc = Column(DateTime(), nullable=False)  # naive UTC (SQLite-safe)

    org_id = Column(String(128), nullable=False)

    license_id = Column(String(128), nullable=False)
    license_name = Column(String(256), nullable=True)

    total_units = Column(Integer, nullable=True)
    consumed_units = Column(Integer, nullable=True)

    subscription_id = Column(String(128), nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    fingerprint = Column(String(64), unique=True, nullable=False)

    alert_type = Column(String(64), nullable=False)
    org = Column(String(128), nullable=False)
    location = Column(String(128), nullable=False)

    severity = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="open")

    first_seen_at = Column(DateTime(), nullable=False)  # naive UTC
    last_seen_at = Column(DateTime(), nullable=False)   # naive UTC
    last_sent_at = Column(DateTime(), nullable=True)    # naive UTC

    details = Column(Text, nullable=True)

