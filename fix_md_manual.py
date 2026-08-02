#!/usr/bin/env python3
"""One-off script to fix common markdownlint issues across all .md files."""
from pathlib import Path
import re

REPO = Path(r"E:\master-repo\modules\app-semptify-fastapi")
SKIP_MD040_MD036 = {REPO / "BUILD_STATE.md"}


def detect_code_language(lines):
    """Infer a language tag for an unlabeled fenced code block."""
    # find first non-blank line inside the block
    first = ""
    for ln in lines:
        s = ln.strip()
        if s:
            first = s
            break
    lower = first.lower()

    # PowerShell / Windows
    if re.search(r"\b(Copy-Item|Get-ChildItem|New-Item|Start-Process|Select-Object|Set-Location|Write-Output|\.ps1|Invoke-Expression)\b", first, re.I):
        return "powershell"
    # Python
    if re.match(r"^(import |from |def |class |async def |await |print\(|if |for |while |try:|with |return |pip |pytest |uvicorn |gunicorn |alembic |docker-compose |fastapi )", first, re.I):
        return "python"
    if re.search(r"\b(python|pip|pytest|uvicorn|gunicorn|alembic|fastapi|sqlalchemy|pydantic|httpx|jinja2)\b", first, re.I):
        return "python"
    # Bash / shell
    if re.match(r"^(\$ |# |git |npm |npx |node |yarn |curl |wget |bash |sh |sudo |apt |choco |cd |mkdir |\.\/|\.\\\S+\.bat|\.\\\S+\.ps1|Start-SEMPTIFY|start-semptify)", first, re.I):
        return "bash"
    # SQL
    if re.match(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH) \b", first, re.I):
        return "sql"
    # JSON
    if re.match(r"^[\[\{]", first) and ('"' in first or "'" in first or ':' in first):
        return "json"
    # HTML
    if re.match(r"^<", first) and re.search(r"<\/?[a-zA-Z][^>]*>", first):
        return "html"
    # JavaScript
    if re.match(r"^(const |let |var |function |async function |class |import |export |console\.)", first):
        return "javascript"
    return "text"


def previous_heading_level(lines, idx):
    """Find the nearest preceding heading and return its level (1-6)."""
    for i in range(idx - 1, -1, -1):
        m = re.match(r"^(#{1,6})\s", lines[i])
        if m:
            return len(m.group(1))
    return 0


def process_file(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines = []
    i = 0
    changed = False

    # --- MD041: first-line h1 (and MD025 guard) ---
    # We need a filename-derived title if the file starts with a non-top heading or non-heading.
    first_content_idx = 0
    has_front_matter = False
    if lines and lines[0].strip() == "---":
        try:
            end_fm = lines.index("---", 1)
            has_front_matter = True
            first_content_idx = end_fm + 1
        except ValueError:
            pass

    # Identify all h1 positions for MD025
    h1_positions = [idx for idx, ln in enumerate(lines) if re.match(r"^#\s", ln)]
    if h1_positions:
        first_h1 = h1_positions[0]
        for pos in h1_positions[1:]:
            if lines[pos].startswith("# "):
                lines[pos] = "##" + lines[pos][1:]
                changed = True

    # Add missing h1 if the first non-FM content is not a top-level heading
    if not h1_positions and (first_content_idx < len(lines)):
        title = path.stem.replace("_", " ").replace("-", " ").strip()
        title = re.sub(r"\.prompt$", " prompt", title, flags=re.I)
        title = re.sub(r"\.readme$", "", title, flags=re.I)
        title = title.title()
        if not title:
            title = "Untitled"
        # Preserve front matter + blank line + h1 + blank line + original first content
        insert_lines = []
        if has_front_matter:
            insert_lines = lines[:first_content_idx] + ["", f"# {title}", ""]
            rest_start = first_content_idx
        else:
            insert_lines = [f"# {title}", ""]
            rest_start = 0
        lines = insert_lines + lines[rest_start:]
        changed = True

    # Recompute split after edits
    text = "\n".join(lines)
    lines = text.splitlines()

    # --- MD036 / MD040 / MD031 around fences ---
    i = 0
    while i < len(lines):
        ln = lines[i]

        # MD036: lines that are only bold/strong
        m = re.match(r"^(\s*)(\*\*|__)(.+?)(\2)\s*$", ln)
        if m:
            indent = m.group(1)
            content = m.group(3).strip()
            # Skip if this looks like it is inside a table (it has surrounding pipes)
            # Skip if content is just a single character or empty
            if content and not re.match(r"^\s*\|", ln):
                if path not in SKIP_MD040_MD036:
                    level = previous_heading_level(lines, i)
                    new_level = min(max(level + 1, 2), 6)
                    new_lines.append(f"{indent}{ '#' * new_level } {content}")
                    changed = True
                    i += 1
                    continue

        # MD040: unlabeled code fence
        fence_match = re.match(r"^(\s*)```\s*$", ln)
        if fence_match:
            indent = fence_match.group(1)
            block_start = i
            j = i + 1
            while j < len(lines):
                if re.match(rf"^{re.escape(indent)}```\s*$", lines[j]):
                    break
                j += 1
            # j is closing fence line or len(lines)
            if j < len(lines):
                content_lines = lines[i+1:j]
                lang = detect_code_language(content_lines)
                new_lines.append(f"{indent}```{lang}")
                new_lines.extend(content_lines)
                new_lines.append(lines[j])
                changed = True
                i = j + 1
                continue

        new_lines.append(ln)
        i += 1

    if changed:
        new_text = "\n".join(new_lines)
        # Ensure single trailing newline
        if not new_text.endswith("\n"):
            new_text += "\n"
        elif new_text.endswith("\n\n"):
            new_text = new_text.rstrip("\n") + "\n"
        path.write_text(new_text, encoding="utf-8")
    return changed


def main():
    md_files = list(REPO.rglob("*.md"))
    for p in md_files:
        if "node_modules" in p.parts:
            continue
        process_file(p)


if __name__ == "__main__":
    main()
