import os
from dotenv import load_dotenv

# Load .env values into environment variables
load_dotenv()

def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    return (v or "").strip()

# Webex auth / org targeting (we'll improve auth later)
WEBEX_ACCESS_TOKEN = env("WEBEX_ACCESS_TOKEN")
WEBEX_ORG_ID = env("WEBEX_ORG_ID", "")

# Local storage
DATABASE_URL = env("DATABASE_URL", "sqlite:///./bullfrog_alerting.db")

# Alerting
WEBEX_INCOMING_WEBHOOK_URL = env("WEBEX_INCOMING_WEBHOOK_URL")
ALERT_COOLDOWN_MINUTES = int(env("ALERT_COOLDOWN_MINUTES", "30"))

# Oauth
WEBEX_CLIENT_ID = env("WEBEX_CLIENT_ID", "")
WEBEX_CLIENT_SECRET = env("WEBEX_CLIENT_SECRET", "")
WEBEX_REFRESH_TOKEN = env("WEBEX_REFRESH_TOKEN", "")

