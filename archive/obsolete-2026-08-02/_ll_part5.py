"""Inject nav+tab items, append 3 new sections."""
import pathlib

p = pathlib.Path(r"c:\Semptify\Semptify-FastAPI\app\templates\pages\law_library.html")
text = p.read_text(encoding="utf-8")

# ── Sidebar nav ──
OLD_NAV = "  <div class=\"nav-item\" onclick=\"showSection('murphys')\">😅 Murphy's &amp; More</div>\n</nav>"
NEW_NAV = (
    "  <div class=\"nav-item\" onclick=\"showSection('murphys')\">😅 Murphy's &amp; More</div>\n"
    "  <div class=\"sidebar-section\">Tools</div>\n"
    "  <div class=\"nav-item\" onclick=\"showSection('statelookup')\">🌎 State Law Lookup</div>\n"
    "  <div class=\"nav-item\" onclick=\"showSection('legalaid')\">⚖️ Free Legal Help</div>\n"
    "  <div class=\"nav-item\" onclick=\"showSection('evictionanswer')\">📄 Eviction Answer</div>\n"
    "</nav>"
)
assert OLD_NAV in text, f"NAV not found. Snippet: {repr(text[text.find('murphys'):text.find('murphys')+120])}"
text = text.replace(OLD_NAV, NEW_NAV, 1)

# ── Tab bar ──
OLD_TAB = "  <button class=\"tab-btn\" onclick=\"showSection('murphys')\">Murphy's</button>\n</div>"
NEW_TAB = (
    "  <button class=\"tab-btn\" onclick=\"showSection('murphys')\">Murphy's</button>\n"
    "  <button class=\"tab-btn\" onclick=\"showSection('statelookup')\">🌎 State Laws</button>\n"
    "  <button class=\"tab-btn\" onclick=\"showSection('legalaid')\">⚖️ Legal Help</button>\n"
    "  <button class=\"tab-btn\" onclick=\"showSection('evictionanswer')\">📄 Answer Tool</button>\n"
    "</div>"
)
assert OLD_TAB in text, f"TAB not found. Snippet: {repr(text[text.find(\"Murphy's</button>\"):text.find(\"Murphy's</button>\")+80])}"
text = text.replace(OLD_TAB, NEW_TAB, 1)

p.write_text(text, encoding="utf-8")
print(f"Nav+tabs done. Lines: {len(text.splitlines())}")
