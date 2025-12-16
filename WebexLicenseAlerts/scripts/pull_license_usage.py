import sys
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

from app.config import WEBEX_ORG_ID
from app.webex_auth import get_access_token
from app.db import engine, Base
from app.models import LicenseSnapshot, Alert  # ensure Base sees tables

WEBEX_API_BASE = "https://webexapis.com/v1"


def utcnow_naive() -> datetime:
    """
    Create a timezone-aware UTC datetime, then strip tzinfo so it is
    SQLite-safe and future-proof.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_licenses(org_id: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {get_access_token()}"}
    params = {}
    if org_id:
        params["orgId"] = org_id

    resp = requests.get(
        f"{WEBEX_API_BASE}/licenses",
        headers=headers,
        params=params,
        timeout=30,
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"Webex API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data.get("items", [])


def main() -> int:
    # Ensure tables exist
    Base.metadata.create_all(engine)

    captured_at = utcnow_naive()

def main(org_id: str) -> int:
    Base.metadata.create_all(engine)

    captured_at = utcnow_naive()
    org_id = (org_id or "").strip()

    items = list_licenses(org_id)
    if not items:
        print(f"No licenses returned for orgId={org_id or '(default-org)'}")
        return 2

    rows = 0
    with Session(engine) as session:
        for lic in items:
            snap = LicenseSnapshot(
                captured_at_utc=captured_at,
                org_id=org_id or "default-org",
                license_id=lic.get("id", ""),
                license_name=lic.get("name"),
                total_units=lic.get("totalUnits"),
                consumed_units=lic.get("consumedUnits"),
                subscription_id=lic.get("subscriptionId"),
            )
            session.add(snap)
            rows += 1
        session.commit()

    print(f"OK: captured {rows} license rows for orgId={org_id or '(default-org)'} at {captured_at.isoformat()} UTC")
    return 0



if __name__ == "__main__":
    try:
        org_id = sys.argv[1] if len(sys.argv) > 1 else ""
        raise SystemExit(main(org_id))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise
 
