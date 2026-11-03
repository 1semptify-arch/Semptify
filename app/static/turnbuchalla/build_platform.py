#!/usr/bin/env python3
"""Regenerate index.html bill sections from the canonical titled draft.

SSOT: ../01_CONTENT/BILL_V2_TITLED_*.md (latest) -> index.html between
<!-- BILLDOC:START --> and <!-- BILLDOC:END -->. Never hand-edit inside
the markers. Run: python build_platform.py
"""
import re, html, sys
from pathlib import Path

HERE = Path(__file__).parent
CONTENT = HERE.parent / "01_CONTENT"
INDEX = HERE / "index.html"


def latest_draft():
    files = sorted(CONTENT.glob("BILL_V2_TITLED_*.md"))
    if not files:
        sys.exit("no BILL_V2_TITLED_*.md found")
    return files[-1]


def esc(s):
    return html.escape(s.strip(), quote=False).replace("**", "")


def emit_section(secnum, title, body_lines, dnotes):
    out = [f'    <section><span class="secnum">{secnum}</span>']
    out.append(f'      <h3>{esc(title)}</h3>')
    bullets = [b for b in body_lines if b.lstrip().startswith("- ")]
    paras = [b for b in body_lines if not b.lstrip().startswith("- ")]
    for p in paras:
        if p.strip():
            out.append(f'      <p>{esc(p)}</p>')
    if bullets:
        out.append('      <ul>')
        for b in bullets:
            out.append(f'        <li>{esc(b.lstrip()[2:])}</li>')
        out.append('      </ul>')
    for d in dnotes:
        out.append(f'      <p class="dnote">{esc(d)}</p>')
    out.append(f'      <a class="annot" href="comment.html?c={secnum}" aria-label="Annotate {secnum}">+</a>')
    out.append('    </section>')
    return out


def convert(md):
    out, i, sec, n = [], 0, 0, 0
    lines = md.splitlines()
    while i < len(lines):
        ln = lines[i].rstrip()
        t = re.match(r"^##\s+TITLE\s+(\S+)\s+—\s+(.*)", ln)
        if t:
            out.append(f'  <p class="title-head" id="t{n if n else 1}">Title {t.group(1)} — {esc(t.group(2))}</p>')
            # italic note line right under a title (not a **X-Y. section start)
            if (i + 1 < len(lines) and lines[i+1].strip().startswith("*")
                    and not re.match(r"^\*\*[IVX]+-\d", lines[i+1].strip())):
                out.append(f'  <p class="title-note">{esc(lines[i+1].strip().strip("*"))}</p>')
                i += 1
            out.append('  <div class="doc">')
            n += 1
            i += 1
            continue
        s = re.match(r"^\*\*([IVX]+-\d+)\.\s*([^*]+?)\*\*\s*(.*)", ln)
        if s:
            body, dnotes = [], []
            j = i + 1
            while j < len(lines) and not re.match(r"^(\*\*[IVX]+-\d+|##\s+TITLE|##\s|---\s*$)", lines[j].strip()):
                l2 = lines[j].strip()
                if not l2:
                    j += 1; continue
                m = re.match(r"^\*\((.*)\)\*$", l2)
                if m:
                    dnotes.append(m.group(1))
                else:
                    body.append(l2)
                j += 1
            out += emit_section(s.group(1), s.group(2).strip().rstrip("."), ([s.group(3)] if s.group(3).strip() else []) + body, dnotes)
            i = j
            continue
        s2 = re.match(r"^\*\*([IVX]+-\d+)\.\*\*\s*(.*)", ln)
        if s2:
            body, dnotes = [], []
            j = i + 1
            while j < len(lines) and not re.match(r"^(\*\*[IVX]+-\d+|##\s+TITLE|##\s|---\s*$)", lines[j].strip()):
                l2 = lines[j].strip()
                if not l2:
                    j += 1; continue
                m = re.match(r"^\*\((.*)\)\*$", l2)
                if m:
                    dnotes.append(m.group(1))
                else:
                    body.append(l2)
                j += 1
            first = s2.group(2).strip()
            title = re.split(r"[.(]", first)[0].strip() or "Section"
            out += emit_section(s2.group(1), title, ([first] if first else []) + body, dnotes)
            i = j
            continue
        h = re.match(r"^###\s+(Preamble.*|Definitions.*)", ln)
        if h:
            if sec == 0:
                out.append('  <p class="title-head" id="findings">Findings &amp; Definitions</p>')
                out.append('  <div class="doc">')
            sec += 1
            out.append(f'    <section><span class="secnum">§·{sec-1}</span>')
            out.append(f'      <h3>{esc(h.group(1))}</h3>')
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("- "):
                out.append(f'      <p>• {esc(lines[j].strip()[2:])}</p>')
                j += 1
            out.append('    </section>')
            i = j
            continue
        if ln.strip() == "---" and out and out[-1] != '  <div class="doc">':
            pass
        i += 1
    # close open doc divs: a doc div opens per title; find count and balance
    opens = sum(1 for l in out if l == '  <div class="doc">')
    return "\n".join(out), opens


def main():
    md = latest_draft().read_text(encoding="utf-8")
    frag, opens = convert(md)
    # balance: close each doc div at the right spots — insert </div> before each subsequent title-head and at end
    lines = frag.split("\n")
    fixed, open_docs = [], 0
    for l in lines:
        if l.startswith('  <p class="title-head"') and open_docs:
            fixed.append('  </div>'); open_docs -= 1
        if l == '  <div class="doc">':
            open_docs += 1
        fixed.append(l)
    while open_docs:
        fixed.append('  </div>'); open_docs -= 1
    frag = "\n".join(fixed)

    page = INDEX.read_text(encoding="utf-8")
    a = page.index("<!-- BILLDOC:START")
    a = page.index("-->", a) + 3
    b = page.index("<!-- BILLDOC:END -->")
    INDEX.write_text(page[:a] + "\n" + frag + "\n  " + page[b:], encoding="utf-8")
    print(f"OK — index.html bill sections regenerated from {latest_draft().name}")


if __name__ == "__main__":
    main()
