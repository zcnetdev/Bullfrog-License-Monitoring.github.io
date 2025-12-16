import os
import hashlib
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, select
)
from sqlalchemy.orm import declarative_base, Session

load_dotenv()

WEBEX_INCOMING_WEBHOOK_URL = os.getenv("WEBEX_INCOMING_WEBHOOK_URL", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bullfrog_alerting.db").strip()

# Cooldown for identical alerts (minutes)
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30"))

engine = create_engine(DATABASE_URL, future=True)
Base = declarative_base()

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    fingerprint = Column(String(64), unique=True, nullable=False)
    alert_type = Column(String(64), nullable=False)
    org = Column(String(128), nullable=False)       # placeholder for now
    location = Column(String(128), nullable=False)  # placeholder for now
    severity = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="open")

    first_seen_at = Column(DateTime(), nullable=False)
    last_seen_at = Column(DateTime(), nullable=False)
    last_sent_at = Column(DateTime(), nullable=True)

    details = Column(Text, nullable=True)

def utcnow() -> datetime:
    return datetime.utcnow()

def make_fingerprint(alert_type: str, org: str, location: str) -> str:
    raw = f"{alert_type}|{org}|{location}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def post_to_webex(markdown: str) -> None:
    if not WEBEX_INCOMING_WEBHOOK_URL:
        raise RuntimeError("WEBEX_INCOMING_WEBHOOK_URL not set")

    resp = requests.post(
        WEBEX_INCOMING_WEBHOOK_URL,
        json={"markdown": markdown},
        timeout=15,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Webex webhook error {resp.status_code}: {resp.text}")

def should_send(last_sent_at: datetime | None) -> bool:
    if last_sent_at is None:
        return True
    return utcnow() - last_sent_at >= timedelta(minutes=ALERT_COOLDOWN_MINUTES)

def emit_alert(alert_type: str, org: str, location: str, severity: str, details: str) -> str:
    """
    Upserts an alert by fingerprint. Sends to Webex only if outside cooldown.
    Returns: "sent" | "suppressed"
    """
    fp = make_fingerprint(alert_type, org, location)
    now = utcnow()

    with Session(engine) as session:
        existing = session.execute(select(Alert).where(Alert.fingerprint == fp)).scalar_one_or_none()

        if existing is None:
            a = Alert(
                fingerprint=fp,
                alert_type=alert_type,
                org=org,
                location=location,
                severity=severity,
                status="open",
                first_seen_at=now,
                last_seen_at=now,
                last_sent_at=None,
                details=details,
            )
            session.add(a)
            session.commit()
            existing = a
        else:
            existing.last_seen_at = now
            existing.severity = severity
            existing.details = details
            session.commit()

        if should_send(existing.last_sent_at):
            # Keep messages consistent and actionable
            msg = (
                f"**Bullfrog Alert**\n"
                f"- Type: `{alert_type}`\n"
                f"- Org: {org}\n"
                f"- Location: {location}\n"
                f"- Severity: **{severity}**\n"
                f"- Details: {details}\n"
                f"- Time (UTC): {now.isoformat()}\n"
                f"- Cooldown: {ALERT_COOLDOWN_MINUTES} minutes"
            )
            post_to_webex(msg)

            existing.last_sent_at = now
            session.commit()
            return "sent"

        return "suppressed"

# --- FastAPI app + scheduler ---

app = FastAPI(title="Bullfrog Evaluator (MVP)")

scheduler = BackgroundScheduler(daemon=True)

def heartbeat_job():
    # Placeholder org/location now; later we’ll use real customer/location identifiers
    emit_alert(
        alert_type="heartbeat",
        org="internal",
        location="evaluator",
        severity="info",
        details="Evaluator is running. This message is deduped by cooldown.",
    )

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(engine)

    # Heartbeat every 5 minutes; dedupe prevents spam.
    scheduler.add_job(heartbeat_job, "interval", minutes=5, id="heartbeat", replace_existing=True)
    scheduler.start()

@app.get("/health")
def health():
    return {"status": "ok", "time_utc": utcnow().isoformat()}

