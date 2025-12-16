import hashlib
from datetime import datetime, timedelta

import requests
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import WEBEX_INCOMING_WEBHOOK_URL, ALERT_COOLDOWN_MINUTES
from app.db import engine
from app.models import Alert

def utcnow_naive() -> datetime:
    return datetime.utcnow()

def make_fingerprint(alert_type: str, org: str, location: str) -> str:
    raw = f"{alert_type}|{org}|{location}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def post_to_webex(markdown: str) -> None:
    if not WEBEX_INCOMING_WEBHOOK_URL:
        raise RuntimeError("WEBEX_INCOMING_WEBHOOK_URL not set in .env")

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
    return utcnow_naive() - last_sent_at >= timedelta(minutes=ALERT_COOLDOWN_MINUTES)

def emit_alert(alert_type: str, org: str, location: str, severity: str, details: str) -> str:
    fp = make_fingerprint(alert_type, org, location)
    now = utcnow_naive()

    with Session(engine) as session:
        existing = session.execute(select(Alert).where(Alert.fingerprint == fp)).scalar_one_or_none()

        if existing is None:
            existing = Alert(
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
            session.add(existing)
            session.commit()
        else:
            existing.last_seen_at = now
            existing.severity = severity
            existing.details = details
            session.commit()

        if should_send(existing.last_sent_at):
            msg = (
                f"**Bullfrog Alert**\n"
                f"- Type: `{alert_type}`\n"
                f"- Org: {org}\n"
                f"- Key: {location}\n"
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

