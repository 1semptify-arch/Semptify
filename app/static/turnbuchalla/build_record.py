#!/usr/bin/env python3
"""build_record.py — render record.html's public ledgers from the registers.

SSOT: ../registers/*.jsonl (case-side, hand-maintained — see
registers/README.md) -> record.html between paired markers:

    <!-- LED:<NAME>:START --> ... <!-- LED:<NAME>:END -->
        inside each <tbody> — receives the <tr> rows, or nothing.
    <!-- LED:<NAME>_EMPTY:START --> ... <!-- LED:<NAME>_EMPTY:END -->
        around the designed empty-state <p class="empty"> — the <p>
        renders while a register is empty and gains a `hidden`
        attribute once rows exist (it is never deleted, so the copy
        stays canonical in the page, not in this script).

Register rows are plain text; every field is HTML-escaped at render —
nothing in a register can inject markup. Lines carrying "_comment" are
documentation, not entries. A row missing every data field is skipped.

Every run that changes record.html appends one row to
registers/builds.jsonl — the page's own Ledger the third.

Never hand-edit inside the markers. Run: python build_record.py
"""
import hashlib
import html
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
REGISTERS = HERE.parent / "registers"
RECORD = HERE / "record.html"
BUILDS = REGISTERS / "builds.jsonl"

# register file -> (LED tag, column order matching record.html's <th>s,
#                   header labels for td[data-label] — used by the stacked
#                   mobile layout in style.css @media (max-width:640px))
LEDDERS = {
    "editions.jsonl": ("EDITIONS", ("edition", "date", "clause", "change"),
                       ("Edition", "Date", "Clause", "Change")),
    "positions.jsonl": ("STANDS", ("name", "role", "stance", "on_record"),
                        ("Name", "Role", "Stance", "On record")),
}

EMPTY_COPY = {
    "BUILDS": "No publish runs entered yet — the log starts when the first build is entered.",
}


def esc(s):
    return html.escape(str(s or "").strip(), quote=False)


def read_register(path, cols):
    """Parse a .jsonl register into row tuples, skipping _comment lines
    and rows with no data fields set."""
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            print(f"  SKIP unparseable line in {path.name}: {ln[:60]}")
            continue
        if "_comment" in e:
            continue
        vals = [e.get(c) for c in cols]
        if not any(str(v or "").strip() for v in vals):
            continue
        rows.append(vals)
    return rows


def tr(vals, labels):
    cells = "".join(
        f'<td data-label="{esc(lab)}">{esc(v)}</td>'
        for lab, v in zip(labels, vals))
    return "    <tr>" + cells + "</tr>"


def set_region(page, tag, inner):
    start = f"<!-- LED:{tag}:START -->"
    end = f"<!-- LED:{tag}:END -->"
    a = page.index(start) + len(start)
    b = page.index(end)
    return page[:a] + inner + page[b:]


def render_ledger(page, tag, rows_html, empty_inner):
    """Fill tbody region with rows (or nothing) and toggle the paired
    empty-state <p>: visible while the register is empty, `hidden` once
    rows exist."""
    if rows_html:
        page = set_region(page, tag, "\n" + "\n".join(rows_html) + "\n  ")
        page = set_region(
            page, f"{tag}_EMPTY",
            '\n  <p class="empty" hidden>' + empty_inner + "</p>\n  ")
    else:
        page = set_region(page, tag, "")
        page = set_region(
            page, f"{tag}_EMPTY",
            '\n  <p class="empty">' + empty_inner + "</p>\n  ")
    return page


def empty_inner_for(page, tag, fallback):
    """Current copy inside the EMPTY markers — keeps page copy canonical
    even across renders (a `hidden` attr on the existing <p> is fine,
    it gets rewritten by render_ledger)."""
    start = f"<!-- LED:{tag}_EMPTY:START -->"
    end = f"<!-- LED:{tag}_EMPTY:END -->"
    try:
        a = page.index(start) + len(start)
        b = page.index(end)
    except ValueError:
        return fallback
    cur = page[a:b]
    # reuse the existing <p class="empty"> inner text if present
    import re
    m = re.search(r'<p class="empty"[^>]*>(.*?)</p>', cur, re.S)
    return m.group(1).strip() if m else fallback


def log_build(what):
    REGISTERS.mkdir(exist_ok=True)
    row = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M"), "what": what}
    with open(BUILDS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _masked(page):
    """Page with the BUILDS ledger regions blanked — used for the
    changed-check so a run that only re-renders the build log itself
    doesn't append yet another log row (feedback loop)."""
    for tag in ("BUILDS", "BUILDS_EMPTY"):
        try:
            page = set_region(page, tag, "")
        except ValueError:
            pass
    return page


def main():
    if not RECORD.exists():
        sys.exit("record.html missing")
    page = RECORD.read_text(encoding="utf-8")
    before = hashlib.sha256(_masked(page).encode("utf-8")).hexdigest()

    counts = {}
    for fname, (tag, cols, labels) in LEDDERS.items():
        rows = read_register(REGISTERS / fname, cols)
        counts[tag] = len(rows)
        empty_inner = empty_inner_for(page, tag, "")
        page = render_ledger(
            page, tag, [tr(r, labels) for r in rows], empty_inner)

    # Ledger the third: the build log renders builds.jsonl itself.
    brows = read_register(BUILDS, ("ts", "what"))
    counts["BUILDS"] = len(brows)
    empty_inner = empty_inner_for(page, "BUILDS", EMPTY_COPY["BUILDS"])
    page = render_ledger(
        page, "BUILDS",
        [tr(r, ("Date", "The build")) for r in brows], empty_inner)

    after = hashlib.sha256(_masked(page).encode("utf-8")).hexdigest()
    if before == after:
        if page != RECORD.read_text(encoding="utf-8"):
            # Build-log backlog: a register row was logged after the last
            # write but only the masked regions differ — catch the ledger
            # up without logging another run (a log line here would never
            # be rendered, and would stay one behind forever).
            RECORD.write_text(page, encoding="utf-8")
            print(f"OK — build log caught up (editions:{counts['EDITIONS']} "
                  f"stands:{counts['STANDS']} builds:{counts['BUILDS']})")
        else:
            print(f"unchanged — record.html already current "
                  f"(editions:{counts['EDITIONS']} stands:{counts['STANDS']} "
                  f"builds:{counts['BUILDS']})")
        return
    # Content changed: log this run first, then re-render the BUILDS
    # region so the page being written already carries its own entry —
    # the log is never left one row behind.
    log_build(f"record.html ledgers rendered — editions:{counts['EDITIONS']} "
              f"stands:{counts['STANDS']}")
    brows = read_register(BUILDS, ("ts", "what"))
    counts["BUILDS"] = len(brows)
    page = render_ledger(
        page, "BUILDS",
        [tr(r, ("Date", "The build")) for r in brows], empty_inner)
    RECORD.write_text(page, encoding="utf-8")
    print(f"OK — record.html rendered (editions:{counts['EDITIONS']} "
          f"stands:{counts['STANDS']} builds:{counts['BUILDS']}); "
          f"run logged to builds.jsonl")


if __name__ == "__main__":
    main()
