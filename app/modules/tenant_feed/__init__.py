"""Tenant Feed Aggregator module.

Merges: timeline events + documents + journal entries + deadlines + letters
into a single chronological feed for the RECORD pillar.

Endpoint:
    GET /api/tenant/feed?type={filter} — returns aggregated feed items

All sources are existing endpoints — this is pure aggregation. No new data
storage. Items are returned sorted chronologically (newest first).
"""

from .router import router
from .service import aggregate_feed, FeedItem

__all__ = ["router", "aggregate_feed", "FeedItem"]
