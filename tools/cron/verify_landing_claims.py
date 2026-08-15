"""Render cron script: hit the dedicated landing-claims verification endpoint.

Uses stdlib only so the cron job does not need to install extra dependencies.
Exit code is non-zero if the request fails, so Render marks the job failed.
"""

import os
import sys
import urllib.request


def main() -> int:
    app_url = os.environ.get("APP_URL", "https://semptify.org").rstrip("/")
    endpoint = f"{app_url}/api/data-freshness/cron/verify-landing-claims"

    req = urllib.request.Request(
        endpoint,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=b"{}",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            print(f"Status: {resp.status}\nBody: {body}")
            if resp.status >= 400:
                print("Verification endpoint returned an error", file=sys.stderr)
                return 1
            return 0
    except Exception as e:
        print(f"Failed to call verification endpoint: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
