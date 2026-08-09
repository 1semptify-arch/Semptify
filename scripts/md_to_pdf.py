"""Convert a markdown file to a styled PDF using Edge headless.

Usage: python scripts/md_to_pdf.py <input.md> <output.pdf>

Requires Microsoft Edge to be installed at the standard Windows path.
"""

import re
import subprocess
import sys
from pathlib import Path

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def md_to_html(md: str) -> str:
    """Minimal markdown -> HTML converter (handles the subset we use)."""
    lines = md.splitlines()
    out = []
    in_list = False
    in_paragraph = []

    def flush_paragraph():
        if in_paragraph:
            out.append("<p>" + " ".join(in_paragraph) + "</p>")
            in_paragraph.clear()

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_paragraph()
            close_list()
            continue
        if line.startswith("# "):
            flush_paragraph()
            close_list()
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            flush_paragraph()
            close_list()
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            flush_paragraph()
            close_list()
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("---"):
            flush_paragraph()
            close_list()
            out.append("<hr>")
        elif line.startswith("- "):
            flush_paragraph()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            flush_paragraph()
            close_list()
            out.append(f"<p><em>{inline(line.strip('*'))}</em></p>")
        else:
            close_list()
            in_paragraph.append(inline(line))
    flush_paragraph()
    close_list()
    return "\n".join(out)


def inline(text: str) -> str:
    # Bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # Italics
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{ size: Letter; margin: 1in; }}
body {{
  font-family: Georgia, "Times New Roman", serif;
  font-size: 11.5pt;
  line-height: 1.55;
  color: #1a1a1a;
  max-width: 6.5in;
  margin: 0 auto;
}}
h1 {{
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 22pt;
  color: #2c3e50;
  border-bottom: 2px solid #2c3e50;
  padding-bottom: 6px;
  margin-top: 0;
}}
h2 {{
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 15pt;
  color: #2c3e50;
  margin-top: 1.4em;
  border-bottom: 1px solid #ccc;
  padding-bottom: 3px;
}}
h3 {{
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 12.5pt;
  color: #34495e;
  margin-top: 1em;
}}
p {{ margin: 0.6em 0; }}
ul {{ margin: 0.4em 0 0.8em 0; padding-left: 1.2em; }}
li {{ margin: 0.25em 0; }}
hr {{
  border: none;
  border-top: 1px solid #bbb;
  margin: 1.2em 0;
}}
em {{ color: #555; }}
strong {{ color: #2c3e50; }}
code {{
  font-family: Consolas, "Courier New", monospace;
  font-size: 10pt;
  background: #f4f4f4;
  padding: 1px 4px;
  border-radius: 3px;
}}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/md_to_pdf.py <input.md> <output.pdf>")
        sys.exit(1)
    md_path = Path(sys.argv[1])
    pdf_path = Path(sys.argv[2]).resolve()
    md_text = md_path.read_text(encoding="utf-8")
    # Extract title from first # heading
    title_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else md_path.stem
    body = md_to_html(md_text)
    html = HTML_TEMPLATE.format(title=title, body=body)
    html_path = md_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML written: {html_path}")

    edge = next((p for p in EDGE_PATHS if Path(p).exists()), None)
    if not edge:
        print("ERROR: Microsoft Edge not found.")
        sys.exit(2)
    cmd = [
        edge,
        "--headless=new",
        "--disable-gpu",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    print("Running Edge headless...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if pdf_path.exists():
        print(f"PDF written: {pdf_path}")
    else:
        print("ERROR: PDF was not created.")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
