"""Journal module — Free-form tenant records.

The Journal module lets tenants log contemporaneous records such as verbal
conversations with the landlord, incidents, repair requests, and notes.
Entries are stored in the database and surfaced in the tenant briefcase.
"""
from app.modules.journal.router import router

__all__ = ["router"]
