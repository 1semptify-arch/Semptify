"""First-pass UX rating sweep — scores every user-facing page on the six
rubric dimensions (docs/ux/PAGE_RATING_RUBRIC.md) plus posture flags.

Source-based heuristic pass over template/static HTML (Jinja stripped).
Automated scores are a first pass — pages are marked review=yes where
heuristics are unreliable (heavy Jinja composition, JS-rendered content).

Usage: python tools/ux_audit.py [--date 2026-09-17]
Writes: docs/ux/page_ratings_<date>.csv and .md (worst-first).
"""

import argparse
import csv
import html.parser
import re
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PAGE_DIRS = [
    (REPO_ROOT / "app/templates/pages", "pages"),
    (REPO_ROOT / "app/templates/public", "public"),
]
STATIC_DIRS = [
    (REPO_ROOT / "static/public", "static-public"),
    (REPO_ROOT / "static/911", "static-911"),
    (REPO_ROOT / "static/onboarding", "static-onboarding"),
    (REPO_ROOT / "static/tenant", "static-tenant"),
    (REPO_ROOT / "static/overlays", "static-overlays"),
]

JARGON = [
    "plaintiff", "defendant", "affidavit", "jurisprudence", "subpoena",
    "indemnify", "heretofore", "whereas", "thereof", "prima facie",
    "statute of limitations", "res judicata",
    # dev-speak that must never reach user copy
    "ssot", "middleware", "api endpoint", "json", "functiongroupcontract",
    "overlay manager", "orchestrator", "backend", "frontend", "repo",
]
MARKETING = [
    "amazing", "best-in-class", "revolutionary", "powerful", "seamless",
    "leverage", "cutting-edge", "world-class", "unlock", "supercharge",
    "game-changer", "ultimate solution", "one-stop",
]
COST_FRAMING = [
    "no cost", "free of charge", "for free", "no subscription",
    "premium tier", "no paywall", "$0", "won't cost", "costs nothing",
    "never pay", "no fee", "free forever",
]
SECURITY_POSTURE = [
    "bank-grade", "military-grade", "military grade", "we take security",
    "state-of-the-art security", "enterprise-grade security",
]
ACCOUNT_LANG = ["sign up", "sign-up", "log in to your account", "subscribe now", "create your account"]
PLACEHOLDER = ["lorem ipsum", "todo:", "fixme", "placeholder text", "coming soon", "under construction"]

GENERIC_BUTTONS = {"submit", "click", "ok", "go", "here", "click here", "continue"}


class PageHTML(html.parser.HTMLParser):
    """Extract structure + visible text, skipping script/style/Jinja."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0  # inside script/style
        self.text = []
        self.links = []       # (href, text)
        self.buttons = []     # text
        self.inputs = []      # {type, has_label_hint}
        self.headings = []    # (level, text)
        self.title = ""
        self.images_no_alt = 0
        self._in_title = False
        self._in_link = None
        self._in_button = False
        self._in_heading = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            self._in_link = a.get("href", "")
            self._buf = []
        elif tag == "button":
            self._in_button = True
            self._buf = []
        elif tag in ("h1", "h2", "h3"):
            self._in_heading = int(tag[1])
            self._buf = []
        elif tag == "input":
            t = a.get("type", "text")
            if t in ("hidden", "submit", "button"):
                if t != "hidden":
                    self.buttons.append(a.get("value", "") or t)
            else:
                labeled = bool(a.get("aria-label") or a.get("aria-labelledby")
                               or a.get("placeholder") or a.get("id"))
                self.inputs.append({"type": t, "labeled": labeled})
        elif tag in ("textarea", "select"):
            labeled = bool(a.get("aria-label") or a.get("aria-labelledby")
                           or a.get("id") or a.get("name"))
            self.inputs.append({"type": tag, "labeled": labeled})
        elif tag == "img" and not a.get("alt"):
            self.images_no_alt += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "a" and self._in_link is not None:
            self.links.append((self._in_link, " ".join(self._buf).strip()))
            self._in_link = None
        elif tag == "button" and self._in_button:
            self.buttons.append(" ".join(self._buf).strip())
            self._in_button = False
        elif tag in ("h1", "h2", "h3") and self._in_heading:
            self.headings.append((self._in_heading, " ".join(self._buf).strip()))
            self._in_heading = None

    def handle_data(self, data):
        if self.skip:
            return
        if self._in_title:
            self.title += data
        if self._in_link is not None or self._in_button or self._in_heading:
            self._buf.append(data)
        self.text.append(data)


def analyze(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    extends = bool(re.search(r"\{%\s*extends", raw))
    # Capture shell-injected content BEFORE stripping Jinja: {% block title %},
    # header_title, and description feed the parent's title/h1/meta.
    block_title = ""
    m = re.search(r"\{%\s*block\s+title\s*%\}(.*?)\{%\s*endblock", raw, re.S)
    if m:
        block_title = m.group(1).strip()
    block_h1 = ""
    m = re.search(r"\{%\s*block\s+header_title\s*%\}(.*?)\{%\s*endblock", raw, re.S)
    if m:
        block_h1 = re.sub(r"<[^>]+>", " ", m.group(1)).strip()
    # Strip Jinja statements/comments, keep expression output as text-ish
    stripped = re.sub(r"\{#.*?#\}", " ", raw, flags=re.S)
    stripped = re.sub(r"\{%.*?%\}", " ", stripped, flags=re.S)
    stripped = re.sub(r"\{\{.*?\}\}", " ", stripped, flags=re.S)

    p = PageHTML()
    p.feed(stripped)

    visible = " ".join(" ".join(p.text).split())
    words = visible.split()
    sentences = [s for s in re.split(r"[.!?]+", visible) if s.strip()]
    avg_sent = (sum(len(s.split()) for s in sentences) / len(sentences)) if sentences else 0
    low = visible.lower()

    flags = []
    for label, phrases in (("cost-framing", COST_FRAMING), ("business-posture", MARKETING),
                           ("security-posture", SECURITY_POSTURE), ("account-lang", ACCOUNT_LANG)):
        hits = [ph for ph in phrases if ph in low]
        if hits:
            flags.append(f"{label}: {', '.join(hits[:4])}")
    placeholder_hits = [ph for ph in PLACEHOLDER if ph in low]
    if placeholder_hits:
        flags.append(f"placeholder: {', '.join(placeholder_hits)}")

    jargon_hits = [j for j in JARGON if j in low]
    mkt_hits = [m for m in MARKETING if m in low]
    dead_links = [h for h, _t in p.links if h in ("#", "javascript:void(0)", "javascript:;")]
    missing_files = []
    for href, _t in p.links:
        if href.startswith(("http", "mailto:", "tel:", "#", "/", "{")) or not href.endswith(".html"):
            continue
        if not (path.parent / href).exists() and not (REPO_ROOT / "static" / href).exists():
            missing_files.append(href)
    generic_btns = [b for b in p.buttons if b.lower().strip() in GENERIC_BUTTONS]
    unlabeled = [i for i in p.inputs if not i["labeled"]]
    has_nav = bool(re.search(r"\{%\s*extends", raw)) or re.search(
        r"<nav|footer|back|home|dashboard", low) is not None

    # --- dimension scores ---
    # 1. ease of use
    s1 = 5
    if unlabeled: s1 -= min(2, len(unlabeled))
    if generic_btns: s1 -= 1
    if dead_links: s1 -= min(2, len(dead_links))
    if missing_files: s1 -= min(2, len(missing_files))
    s1 = max(1, s1)

    # 2. user-friendliness
    s2 = 5
    if jargon_hits: s2 -= min(2, len(jargon_hits))
    if mkt_hits: s2 -= 1
    if avg_sent > 28: s2 -= 1
    s2 = max(1, s2)

    # 3. ease of understanding
    has_h1 = any(l == 1 for l, _ in p.headings) or bool(block_h1)
    has_headings = bool(p.headings) or bool(block_h1)
    has_title = bool(p.title.strip() or block_title)
    s3 = 2 + (1 if has_title else 0) + (1 if has_h1 else 0) + (1 if has_headings else 0)
    if not has_title and not has_h1:
        s3 = 1
    s3 = min(5, s3)

    # 4. navigation
    s4 = 5
    if dead_links: s4 -= min(2, len(dead_links))
    if missing_files: s4 -= min(2, len(missing_files))
    if not has_nav and not extends: s4 -= 1
    if not p.links and len(words) < 100: s4 -= 1
    s4 = max(1, s4)

    # 5. clear-cut direction
    n_actions = len(p.buttons) + len([1 for h, t in p.links
                                      if t and len(t.split()) <= 5 and not h.startswith("#")])
    if n_actions == 0:
        s5 = 3 if len(words) < 100 else 4  # pure info page may not need action
    elif n_actions <= 4:
        s5 = 5
    elif n_actions <= 8:
        s5 = 4
    else:
        s5 = 2
    s5 = max(1, s5)

    # 6. information value
    nw = len(words)
    if placeholder_hits:
        s6 = 2
    elif nw < 40:
        s6 = 2
    elif nw < 150:
        s6 = 4
    elif nw <= 2200:
        s6 = 5
    else:
        s6 = 3
    # posture flags ding related dims
    if any(f.startswith(("cost-framing", "business-posture", "security-posture", "account-lang"))
           for f in flags):
        s2 = max(1, s2 - 1)
        s6 = max(1, s6 - 1)

    review = "yes" if extends or len(p.buttons) == 0 and "fetch(" in raw else "no"
    overall = round((s1 + s2 + s3 + s4 + s5 + s6) / 6, 1)

    return {
        "page": path.name, "dir": path.parent.name + "/" + path.name,
        "scores": [s1, s2, s3, s4, s5, s6], "overall": overall,
        "words": nw, "actions": n_actions, "jargon": jargon_hits[:5],
        "dead_links": len(dead_links), "missing_files": missing_files[:4],
        "flags": flags, "extends": extends, "review": review,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    files = []
    for d, _tag in PAGE_DIRS + STATIC_DIRS:
        if d.is_dir():
            files.extend(sorted(d.glob("*.html")))

    rows = [analyze(f) for f in files]
    rows.sort(key=lambda r: r["overall"])

    out_dir = REPO_ROOT / "docs/ux"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"page_ratings_{args.date}.csv"
    md_path = out_dir / f"page_ratings_{args.date}.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page", "file", "overall", "ease_use", "friendliness", "understanding",
                    "navigation", "direction", "info_value", "words", "actions",
                    "flags", "jargon", "dead_links", "missing_files", "extends", "review"])
        for r in rows:
            w.writerow([r["page"], r["dir"], r["overall"], *r["scores"], r["words"],
                        r["actions"], "; ".join(r["flags"]), ", ".join(r["jargon"]),
                        r["dead_links"], ", ".join(r["missing_files"]),
                        r["extends"], r["review"]])

    lines = [
        f"# Page Usability Ratings — {args.date}",
        "",
        "First-pass automated sweep per `PAGE_RATING_RUBRIC.md`. Worst-first.",
        "review=yes means Jinja/JS composition makes the source score unreliable — eye-pass it.",
        "",
        "| Score | Page | EU | UF | Und | Nav | Dir | IV | Flags |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r["scores"]
        flag_txt = "; ".join(r["flags"])[:90] or "—"
        lines.append(f"| {r['overall']} | `{r['dir']}` | {s[0]} | {s[1]} | {s[2]} | {s[3]} | {s[4]} | {s[5]} | {flag_txt} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    flagged = [r for r in rows if r["flags"]]
    print(f"pages: {len(rows)}  ->  {csv_path.name}, {md_path.name}")
    print(f"flagged pages: {len(flagged)}")
    print("worst 10:")
    for r in rows[:10]:
        print(f"  {r['overall']:>3} {r['dir']}  flags={len(r['flags'])} review={r['review']}")


if __name__ == "__main__":
    main()
