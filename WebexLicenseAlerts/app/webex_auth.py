import time
import requests

from app.config import (
    WEBEX_CLIENT_ID,
    WEBEX_CLIENT_SECRET,
    WEBEX_REFRESH_TOKEN,
)

# In-memory token cache (per process)
_TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0,
}

def get_access_token() -> str:
    """
    Returns a valid Webex access token using the Service App refresh_token flow.
    Caches the token in memory and refreshes when nearing expiration.
    """
    now = int(time.time())

    # Return cached token if still valid
    if _TOKEN_CACHE["access_token"] and now < (_TOKEN_CACHE["expires_at"] - 60):
        return _TOKEN_CACHE["access_token"]

    if not WEBEX_CLIENT_ID or not WEBEX_CLIENT_SECRET or not WEBEX_REFRESH_TOKEN:
        raise RuntimeError(
            "Missing WEBEX_CLIENT_ID / WEBEX_CLIENT_SECRET / WEBEX_REFRESH_TOKEN in .env"
        )

    data = {
        "grant_type": "refresh_token",
        "client_id": WEBEX_CLIENT_ID,
        "client_secret": WEBEX_CLIENT_SECRET,
        "refresh_token": WEBEX_REFRESH_TOKEN,
    }

    resp = requests.post(
        "https://webexapis.com/v1/access_token",
        data=data,  # application/x-www-form-urlencoded
        timeout=30,
    )

    if resp.status_code >= 300:
        raise RuntimeError(
            f"Token refresh failed ({resp.status_code}): {resp.text}"
        )

    j = resp.json()

    if "access_token" not in j:
        raise RuntimeError(
            f"Token endpoint did not return access_token. Keys: {list(j.keys())}"
        )

    access_token = str(j["access_token"]).strip()
    expires_in = int(j.get("expires_in", 3600))

    if not access_token or access_token.lower() == "none" or len(access_token) <50:
        raise RuntimeError(f"Received invalid access_token (len={len(access_token)}). Check Service App credentials/refresh token.")

    # NOTE: Webex may rotate refresh tokens. We warn but do not auto-write secrets.
    if "refresh_token" in j and j["refresh_token"] != WEBEX_REFRESH_TOKEN:
        print(
            "NOTICE: Webex returned a new refresh_token. "
            "Update WEBEX_REFRESH_TOKEN in .env to avoid future failures."
        )

    _TOKEN_CACHE["access_token"] = access_token
    _TOKEN_CACHE["expires_at"] = now + expires_in

    return access_token

