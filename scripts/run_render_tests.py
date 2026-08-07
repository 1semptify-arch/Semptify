"""
Semptify Render Test Runner
============================
Run this AFTER Render deploy is live to test the production server.

Categories:
  1. SMOKE TESTS -- basic endpoint availability on live server
  2. LAW LIBRARY API -- verify law linker data on production
  3. PYTEST FIXTURE TESTS -- run via pytest against live server (if configured)

Usage (on Render shell or locally with server running):
    python scripts/run_render_tests.py
    python scripts/run_render_tests.py --base-url https://semptify.org
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

DEFAULT_BASE = "http://localhost:8000"

PASS = 0
FAIL = 0
RESULTS = []


def record(name, status, detail=""):
    global PASS, FAIL
    if status == "PASS":
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append((name, status, detail))
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))


def http_get(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SemptifyTestRunner/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def run_smoke_tests(base):
    print("\n" + "=" * 70)
    print("  CATEGORY 1: SMOKE TESTS (endpoint availability)")
    print("=" * 70)

    endpoints = [
        ("/", "Root page"),
        ("/healthz", "Health check"),
        ("/law-library", "Law library page"),
        ("/api/law-library/links", "Law library links API"),
        ("/api/law-library/statutes", "Statutes API"),
        ("/api/law-library/case-law", "Case law API"),
        ("/api/workflow/case-state", "Workflow case state"),
        ("/api/workflow/contracts/welcome", "Welcome contract"),
        ("/ws/status", "WebSocket status"),
    ]

    for path, desc in endpoints:
        status, body = http_get(base + path)
        if status == 200:
            record(f"GET {path} ({desc})", "PASS", "200 OK")
        elif status is None:
            record(f"GET {path} ({desc})", "FAIL", body[:100])
        else:
            record(f"GET {path} ({desc})", "FAIL", f"HTTP {status}")


def run_law_library_tests(base):
    print("\n" + "=" * 70)
    print("  CATEGORY 2: LAW LIBRARY API (data integrity)")
    print("=" * 70)

    # Links endpoint
    status, body = http_get(base + "/api/law-library/links")
    if status != 200:
        record("law-library/links", "FAIL", f"HTTP {status}")
        return
    try:
        data = json.loads(body)
        links = data.get("links", data) if isinstance(data, dict) else data
        if isinstance(links, list):
            record("links returned", "PASS", f"{len(links)} links")
            https_count = sum(
                1 for l in links if isinstance(l, dict) and str(l.get("official_url", "")).startswith("https://")
            )
            record("all URLs are https", "PASS" if https_count == len(links) else "FAIL", f"{https_count}/{len(links)}")
        else:
            record("links returned", "FAIL", "not a list")
    except json.JSONDecodeError as e:
        record("law-library/links JSON", "FAIL", str(e))

    # Statutes
    status, body = http_get(base + "/api/law-library/statutes")
    if status == 200:
        try:
            data = json.loads(body)
            stats = data if isinstance(data, list) else data.get("statutes", data.get("items", []))
            record("statutes returned", "PASS", f"{len(stats)} statutes")
        except json.JSONDecodeError:
            record("statutes JSON", "FAIL", "invalid JSON")

    # Case law
    status, body = http_get(base + "/api/law-library/case-law")
    if status == 200:
        try:
            data = json.loads(body)
            cases = data if isinstance(data, list) else data.get("cases", data.get("items", []))
            record("case-law returned", "PASS", f"{len(cases)} cases")
        except json.JSONDecodeError:
            record("case-law JSON", "FAIL", "invalid JSON")


def final_report(base):
    print("\n" + "=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)
    print(f"\n  Server: {base}")
    print(f"  Date:  {datetime.now(UTC).isoformat()}")
    print(f"\n  PASS: {PASS}")
    print(f"  FAIL: {FAIL}")
    print(f"  TOTAL: {PASS + FAIL}")

    if FAIL > 0:
        print("\n  FAILED TESTS:")
        for name, status, detail in RESULTS:
            if status == "FAIL":
                print(f"    {name}: {detail}")

    print("\n" + "=" * 70)
    print("\n  NOTE: To run the full pytest suite against this server:")
    print("    pytest tests/ -v --tb=short")
    print("  (requires conftest.py DB fixture fix or running against live DB)")
    print()
    return FAIL == 0


def main():
    parser = argparse.ArgumentParser(description="Semptify Render test runner")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="Base URL of server to test")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print("\n" + "=" * 70)
    print("  SEMPTIFY RENDER TEST RUNNER")
    print(f"  Target: {base}")
    print("=" * 70)

    run_smoke_tests(base)
    run_law_library_tests(base)
    ok = final_report(base)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
