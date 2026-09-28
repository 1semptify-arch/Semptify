"""Call Manager — proactive outreach desk for the tenant's own case work.

An ACT!-style call desk: pick a contact, get an interactive script for that
call type, tap outcomes instead of typing, and the module writes the
follow-up into calendar, journal, and the timeline automatically.
"""

from app.modules.call_manager.router import router

__all__ = ["router"]
