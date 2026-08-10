"""Legacy legal-help page fragment.

The generated fragment is retained as a minimal parseable module. The
application's current templates provide the active navigation and tabs.
"""

EVICTION_NAV = '  <div class="nav-item" onclick="showSection(\'evictionanswer\')">Eviction Answer</div>\n'
ANSWER_TAB = '  <button class="tab-btn" onclick="showSection(\'evictionanswer\')">Answer Tool</button>\n'


def main() -> None:
    """Print the retained fragment for manual inspection."""
    print(EVICTION_NAV + ANSWER_TAB)


if __name__ == "__main__":
    main()
