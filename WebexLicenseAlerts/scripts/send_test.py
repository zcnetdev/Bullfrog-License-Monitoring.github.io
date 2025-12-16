import os
import sys
import requests
from dotenv import load_dotenv

def main() -> int:
    load_dotenv()

    webhook_url = os.getenv("WEBEX_INCOMING_WEBHOOK_URL")
    if not webhook_url:
        print("ERROR: WEBEX_INCOMING_WEBHOOK_URL is not set. Check your .env file.", file=sys.stderr)
        return 1

    payload = {
        "markdown": "**Bullfrog Alerting**\nStep 2 test: Python + .env + webhook posting is working."
    }

    resp = requests.post(webhook_url, json=payload, timeout=15)
    if resp.status_code >= 300:
        print(f"ERROR: Webhook POST failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        return 2

    print("OK: Message posted to Webex space.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

