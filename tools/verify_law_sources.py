"""Law Library source-verification lane (design-doc gap #4).

Fetches every enriched Law Library entry's ``official_url`` and reports which
links are live, moved, blocked, or dead. This is the build-time check that
backs the ``last_verified`` dates in ``app/core/law_source_registry.py`` — run
it before bumping those dates so a "verified" badge always means a human (or
agent) actually fetched the source recently.

Report-only: this tool never edits registry dates. Update them manually after
reviewing the output — that keeps the human publish gate intact.

Usage:
    cd modules/app-semptify-fastapi
    .\\venv311\\Scripts\\python.exe tools/verify_law_sources.py
    .\\venv311\\Scripts\\python.exe tools/verify_law_sources.py --source "Minnesota Revisor of Statutes" --limit 5

Exit code 0 = every checked URL live; 1 = at least one failure/blocked.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import pathlib
import socket
import sys
import urllib.error
import urllib.request
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
socket.setdefaulttimeout(15)

from app.modules.law_library.router import (  # noqa: E402
    ALL_LAWS,
    CASE_LAW_DATABASE,
    DAKOTA_COUNTY_RULES,
)

UA = "SemptifyLawLibraryVerifier/1.0 (+https://semptify.org; link-health check)"


def collect_entries() -> list[dict]:
    rows = []
    for law_id, e in ALL_LAWS.items():
        rows.append({"kind": "statute", "id": law_id, "citation": e.get("citation", ""), "url": e.get("official_url"), "source": e.get("source_name")})
    for c in CASE_LAW_DATABASE:
        rows.append({"kind": "case", "id": c.get("id", "?"), "citation": c.get("citation", ""), "url": c.get("official_url"), "source": c.get("source_name")})
    for rule_id, e in DAKOTA_COUNTY_RULES.items():
        rows.append({"kind": "rule", "id": rule_id, "citation": e.get("rule_number", ""), "url": e.get("official_url"), "source": e.get("source_name")})
    return rows


def check_url(url: str) -> tuple[int | None, str]:
    """Return (status_code, note). Reads only the first chunk, then closes."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read(1024)
            return resp.status, "live"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            return e.code, "blocked — likely bot-filtered, needs human check"
        if e.code == 404:
            return e.code, "not found"
        return e.code, "http error"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Law Library official-source links")
    parser.add_argument("--source", help="Only check entries from this source_name")
    parser.add_argument("--limit", type=int, help="Only check the first N entries")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent fetches (default 6)")
    args = parser.parse_args()

    entries = collect_entries()
    if args.source:
        entries = [e for e in entries if e["source"] == args.source]
    if args.limit:
        entries = entries[: args.limit]

    missing = [e for e in entries if not e["url"]]
    checkable = [e for e in entries if e["url"]]
    print(f"Checking {len(checkable)} official-source links ({len(missing)} entries have no URL)\n")
    for e in missing:
        print(f"  NO-URL   {e['kind']:<8} {e['id']:<32} {e['citation']}")

    results: list[tuple[dict, int | None, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {pool.submit(check_url, e["url"]): e for e in checkable}
        for future in concurrent.futures.as_completed(future_map):
            e = future_map[future]
            status, note = future.result()
            results.append((e, status, note))
            mark = "OK " if status and 200 <= status < 400 else "FAIL"
            print(f"  {mark} {status or '---':<4} {e['kind']:<8} {e['id']:<32} {note}")

    print("\n--- Summary by source ---")
    by_source: dict[str, Counter] = {}
    for e, status, note in results:
        bucket = by_source.setdefault(e["source"] or "unknown", Counter())
        bucket["ok" if status and 200 <= status < 400 else "fail"] += 1
        if not (status and 200 <= status < 400):
            bucket[f"{status}:{note}"] += 0  # keep detail in the per-entry lines
    for source, counts in sorted(by_source.items()):
        print(f"  {source}: {counts['ok']} live / {counts['fail']} failed")

    failures = [r for r in results if not (r[1] and 200 <= r[1] < 400)]
    print(f"\n{len(results) - len(failures)}/{len(results)} links live; {len(failures)} need attention; {len(missing)} entries have no URL")
    return 1 if failures or missing else 0


if __name__ == "__main__":
    sys.exit(main())
