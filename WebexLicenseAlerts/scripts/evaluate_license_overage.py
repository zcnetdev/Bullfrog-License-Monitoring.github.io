import sys
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db import engine, Base
from app.models import LicenseSnapshot, Alert
from app.alerts import emit_alert

def main() -> int:
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        latest_ts = session.execute(
            select(func.max(LicenseSnapshot.captured_at_utc))
        ).scalar_one_or_none()

        if not latest_ts:
            print("No license snapshots found. Run: python -m scripts.pull_license_usage")
            return 2

        snaps = session.execute(
            select(LicenseSnapshot).where(LicenseSnapshot.captured_at_utc == latest_ts)
        ).scalars().all()

    overages = []
    for s in snaps:
        if s.total_units is None or s.consumed_units is None:
            continue
        if s.consumed_units > s.total_units:
            overages.append(s)

    if not overages:
        print(f"OK: No overages detected in latest snapshot ({latest_ts.isoformat()} UTC).")
        return 0

    sent = 0
    suppressed = 0

    # Emit one alert per license SKU (actionable and stable)
    for s in overages:
        org = s.org_id
        key = s.license_name or s.license_id

        details = (
            f"License overage detected.\n"
            f"- License: {s.license_name or '(no name)'}\n"
            f"- License ID: {s.license_id}\n"
            f"- Consumed: {s.consumed_units}\n"
            f"- Entitled: {s.total_units}\n"
            f"- Overage: {s.consumed_units - s.total_units}\n"
            f"- Snapshot (UTC): {latest_ts.isoformat()}"
        )

        result = emit_alert(
            alert_type="license_overage",
            org=org,
            location=key,
            severity="high",
            details=details,
        )

        if result == "sent":
            sent += 1
        else:
            suppressed += 1

    print(f"Overages: {len(overages)}. Alerts sent: {sent}. Suppressed: {suppressed}.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise

