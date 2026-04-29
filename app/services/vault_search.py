"""
ALL-IN-ONE Unified Evidence Vault — Search & Query Service

This service provides deep search, timeline queries, and filtering capabilities
for the unified vault. It leverages PostgreSQL JSONB GIN indexes for performant
metadata and location searching.

Function Group: vault_search
Purpose: Deep search and timeline queries for unified vault.

Search Capabilities:
- Deep metadata search (JSONB text search)
- Location-based search (GPS, coordinates)
- Incident-based filtering
- Timeline ordering (event_time, record_time, semptify_entry_time)
- Multi-criteria filtering (type, severity, status, tags)
- Date range queries
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import select, and_, or_, func, text, desc, asc
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.models.models import VaultItem, Incident, VaultAuditLog

VAULT_SEARCH_FUNCTION_GROUP = "vault_search"

# Register module contract
register_function_group(
    FunctionGroupContract(
        module="vault",
        group_name=VAULT_SEARCH_FUNCTION_GROUP,
        title="Vault Search Service",
        description="Deep search, timeline queries, and filtering for unified vault with JSONB GIN index support.",
        inputs=(
            "user_id",
            "search_criteria",
            "timeline_mode",
        ),
        outputs=(
            "items",
            "total_count",
            "timeline_sequence",
        ),
        dependencies=(
            "VaultItem model",
            "PostgreSQL GIN indexes",
            "JSONB metadata",
        ),
        deterministic=True,
    )
)


class TimelineMode(str, Enum):
    """Timeline ordering modes (three-timestamp model)."""
    EVENT_TIME = "event_time"           # Factual occurrence time
    RECORD_TIME = "record_time"         # When evidence created
    SEMPTIFY_ENTRY_TIME = "semptify_entry_time"  # When added to system
    CREATED_AT = "created_at"           # Internal creation timestamp


class SortOrder(str, Enum):
    """Sort order for results."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class SearchCriteria:
    """
    Search criteria for vault items.
    
    All fields are optional; omitted fields are not filtered.
    """
    # Text search
    query: Optional[str] = None  # General text search across title, summary, metadata
    metadata_query: Optional[str] = None  # Deep search in JSONB metadata
    
    # Classification filters
    item_type: Optional[str | list[str]] = None
    folder: Optional[str] = None
    tags: Optional[list[str]] = None  # Must have all specified tags
    
    # Relationship filters
    related_incident_id: Optional[int] = None
    
    # Status filters
    severity: Optional[str | list[str]] = None  # critical, high, normal, low
    status: Optional[str | list[str]] = None    # pending, verified, disputed, archived
    source: Optional[str] = None
    
    # Location search
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    location_radius_meters: Optional[float] = None  # For geo-radius search
    
    # Date range filters (applied to selected timeline mode)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Pagination
    offset: int = 0
    limit: int = 100
    
    # Sorting
    timeline_mode: TimelineMode = TimelineMode.EVENT_TIME
    sort_order: SortOrder = SortOrder.DESC


@dataclass
class SearchResult:
    """Result of vault search."""
    items: list[VaultItem] = field(default_factory=list)
    total_count: int = 0
    has_more: bool = False
    timeline_sequence: list[dict[str, Any]] = field(default_factory=list)


class VaultSearchService:
    """
    Service for searching and querying the unified vault.
    
    Features:
    - Deep metadata search via JSONB GIN indexes
    - Timeline ordering by any of three timestamps
    - Multi-criteria filtering
    - Incident-based grouping
    - Location-based search
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _build_base_query(self, user_id: str) -> select:
        """Build base query with user filter."""
        return select(VaultItem).where(VaultItem.user_id == user_id)
    
    def _apply_text_search(self, query: select, criteria: SearchCriteria) -> select:
        """Apply general text search across title and summary."""
        if not criteria.query:
            return query
        
        search_pattern = f"%{criteria.query}%"
        return query.where(
            or_(
                VaultItem.title.ilike(search_pattern),
                VaultItem.summary.ilike(search_pattern),
            )
        )
    
    def _apply_metadata_search(self, query: select, criteria: SearchCriteria) -> select:
        """
        Apply deep metadata search using JSONB.
        
        Uses PostgreSQL's JSONB text containment for efficient searching
        through nested metadata structures.
        """
        if not criteria.metadata_query:
            return query
        
        # Use PostgreSQL's JSONB text search
        # Cast metadata to text and search
        search_term = f"%{criteria.metadata_query}%"
        return query.where(
            func.cast(VaultItem.metadata, JSONB).cast(JSONB).cast(str).ilike(search_term)
        )
    
    def _apply_classification_filters(
        self, query: select, criteria: SearchCriteria
    ) -> select:
        """Apply item type, folder, and tag filters."""
        
        # Item type filter
        if criteria.item_type:
            if isinstance(criteria.item_type, list):
                query = query.where(VaultItem.item_type.in_(criteria.item_type))
            else:
                query = query.where(VaultItem.item_type == criteria.item_type)
        
        # Folder filter
        if criteria.folder:
            query = query.where(VaultItem.folder == criteria.folder)
        
        # Tags filter (must have ALL specified tags)
        if criteria.tags:
            # JSONB containment: tags @> ["tag1", "tag2"]
            query = query.where(
                VaultItem.tags.contains(criteria.tags)
            )
        
        return query
    
    def _apply_relationship_filters(
        self, query: select, criteria: SearchCriteria
    ) -> select:
        """Apply incident and source filters."""
        
        if criteria.related_incident_id is not None:
            query = query.where(
                VaultItem.related_incident_id == criteria.related_incident_id
            )
        
        if criteria.source:
            query = query.where(VaultItem.source == criteria.source)
        
        return query
    
    def _apply_status_filters(self, query: select, criteria: SearchCriteria) -> select:
        """Apply severity and status filters."""
        
        # Severity filter
        if criteria.severity:
            if isinstance(criteria.severity, list):
                query = query.where(VaultItem.severity.in_(criteria.severity))
            else:
                query = query.where(VaultItem.severity == criteria.severity)
        
        # Status filter
        if criteria.status:
            if isinstance(criteria.status, list):
                query = query.where(VaultItem.status.in_(criteria.status))
            else:
                query = query.where(VaultItem.status == criteria.status)
        
        return query
    
    def _apply_date_range(self, query: select, criteria: SearchCriteria) -> select:
        """
        Apply date range filter based on selected timeline mode.
        
        This is the key feature of the three-timestamp model - you can
        filter by event time, record time, or semptify entry time.
        """
        date_column = self._get_timeline_column(criteria.timeline_mode)
        
        if criteria.date_from:
            query = query.where(date_column >= criteria.date_from)
        
        if criteria.date_to:
            query = query.where(date_column <= criteria.date_to)
        
        return query
    
    def _get_timeline_column(self, mode: TimelineMode):
        """Get the SQL column for the selected timeline mode."""
        column_map = {
            TimelineMode.EVENT_TIME: VaultItem.event_time,
            TimelineMode.RECORD_TIME: VaultItem.record_time,
            TimelineMode.SEMPTIFY_ENTRY_TIME: VaultItem.semptify_entry_time,
            TimelineMode.CREATED_AT: VaultItem.created_at,
        }
        return column_map[mode]
    
    def _apply_sorting(self, query: select, criteria: SearchCriteria) -> select:
        """Apply sorting based on timeline mode and sort order."""
        date_column = self._get_timeline_column(criteria.timeline_mode)
        
        if criteria.sort_order == SortOrder.ASC:
            return query.order_by(asc(date_column))
        else:
            return query.order_by(desc(date_column))
    
    async def search(self, user_id: str, criteria: SearchCriteria) -> SearchResult:
        """
        Execute search with given criteria.
        
        Args:
            user_id: User ID to filter by
            criteria: SearchCriteria with all filter conditions
        
        Returns:
            SearchResult with items, count, and timeline sequence
        """
        # Build query
        query = self._build_base_query(user_id)
        query = self._apply_text_search(query, criteria)
        query = self._apply_metadata_search(query, criteria)
        query = self._apply_classification_filters(query, criteria)
        query = self._apply_relationship_filters(query, criteria)
        query = self._apply_status_filters(query, criteria)
        query = self._apply_date_range(query, criteria)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0
        
        # Apply sorting and pagination
        query = self._apply_sorting(query, criteria)
        query = query.offset(criteria.offset).limit(criteria.limit + 1)  # +1 to check has_more
        
        # Execute
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Check if there are more results
        has_more = len(items) > criteria.limit
        items = items[:criteria.limit]  # Remove the extra item
        
        # Build timeline sequence for UI
        timeline_sequence = self._build_timeline_sequence(items, criteria.timeline_mode)
        
        return SearchResult(
            items=list(items),
            total_count=total_count,
            has_more=has_more,
            timeline_sequence=timeline_sequence,
        )
    
    def _build_timeline_sequence(
        self, items: list[VaultItem], timeline_mode: TimelineMode
    ) -> list[dict[str, Any]]:
        """
        Build timeline sequence for UI presentation.
        
        Each item gets a sequence number and displays all three timestamps
        for the three-timestamp timeline UI.
        """
        sequence = []
        for idx, item in enumerate(items, start=1):
            sequence.append({
                "sequence": idx,
                "item_id": item.item_id,
                "title": item.title,
                "item_type": item.item_type,
                # All three timestamps for three-timestamp UI
                "event_time": item.event_time.isoformat() if item.event_time else None,
                "record_time": item.record_time.isoformat() if item.record_time else None,
                "semptify_entry_time": item.semptify_entry_time.isoformat() if item.semptify_entry_time else None,
                # Primary sort timestamp (based on timeline mode)
                "sort_timestamp": self._get_sort_timestamp(item, timeline_mode),
                "severity": item.severity,
                "status": item.status,
                "folder": item.folder,
                "tags": item.tags,
            })
        return sequence
    
    def _get_sort_timestamp(self, item: VaultItem, mode: TimelineMode) -> Optional[str]:
        """Get the primary sort timestamp for display."""
        timestamp_map = {
            TimelineMode.EVENT_TIME: item.event_time,
            TimelineMode.RECORD_TIME: item.record_time,
            TimelineMode.SEMPTIFY_ENTRY_TIME: item.semptify_entry_time,
            TimelineMode.CREATED_AT: item.created_at,
        }
        ts = timestamp_map[mode]
        return ts.isoformat() if ts else None
    
    async def get_timeline_by_incident(
        self,
        user_id: str,
        incident_id: int,
        timeline_mode: TimelineMode = TimelineMode.EVENT_TIME,
    ) -> SearchResult:
        """
        Get timeline of all items for a specific incident.
        
        Args:
            user_id: User ID
            incident_id: Incident ID to filter by
            timeline_mode: Which timestamp to order by
        
        Returns:
            SearchResult with incident timeline
        """
        criteria = SearchCriteria(
            related_incident_id=incident_id,
            timeline_mode=timeline_mode,
            sort_order=SortOrder.ASC,
            limit=1000,  # Higher limit for full timeline
        )
        return await self.search(user_id, criteria)
    
    async def deep_metadata_search(
        self,
        user_id: str,
        metadata_field: str,
        value: Any,
    ) -> SearchResult:
        """
        Search for items with specific metadata field value.
        
        Example:
            # Find all items with metadata.landlord = "ABC Management"
            results = await service.deep_metadata_search(
                user_id="abc123",
                metadata_field="landlord",
                value="ABC Management"
            )
        """
        # Use JSONB containment for exact match
        metadata_filter = {metadata_field: value}
        
        query = (
            select(VaultItem)
            .where(VaultItem.user_id == user_id)
            .where(VaultItem.metadata.contains(metadata_filter))
            .order_by(desc(VaultItem.event_time))
        )
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return SearchResult(
            items=list(items),
            total_count=len(items),
            has_more=False,
            timeline_sequence=self._build_timeline_sequence(items, TimelineMode.EVENT_TIME),
        )
    
    async def location_search(
        self,
        user_id: str,
        lat: float,
        lon: float,
        radius_meters: float = 1000,
    ) -> SearchResult:
        """
        Search for items near a geographic location.
        
        Assumes location_data contains {"gps": {"lat": X, "lon": Y}}.
        
        Note: For production, consider using PostGIS for proper geo queries.
        This implementation uses a simple bounding box approximation.
        """
        # Approximate degrees per meter (varies by latitude)
        # At equator: 1 degree ≈ 111km
        degrees_per_meter = 1.0 / 111000.0
        lat_delta = radius_meters * degrees_per_meter
        lon_delta = radius_meters * degrees_per_meter / max(abs(lat) * 0.01745, 0.001)
        
        # Build query for location data within bounding box
        # This is a simplified approach - PostGIS would be better for production
        query = (
            select(VaultItem)
            .where(VaultItem.user_id == user_id)
            .where(VaultItem.location_data.isnot(None))
            .order_by(desc(VaultItem.event_time))
        )
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Filter items by actual distance (in Python for simplicity)
        # Production: Use PostGIS ST_DWithin
        nearby_items = []
        for item in items:
            if item.location_data:
                gps = item.location_data.get("gps", {})
                item_lat = gps.get("lat")
                item_lon = gps.get("lon")
                if item_lat and item_lon:
                    # Simple distance check (would use Haversine for production)
                    if (abs(item_lat - lat) < lat_delta and 
                        abs(item_lon - lon) < lon_delta):
                        nearby_items.append(item)
        
        return SearchResult(
            items=nearby_items,
            total_count=len(nearby_items),
            has_more=False,
            timeline_sequence=self._build_timeline_sequence(nearby_items, TimelineMode.EVENT_TIME),
        )


# Convenience functions

async def search_vault(
    db: AsyncSession,
    user_id: str,
    query: Optional[str] = None,
    item_type: Optional[str] = None,
    incident_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    timeline_mode: TimelineMode = TimelineMode.EVENT_TIME,
    limit: int = 100,
) -> SearchResult:
    """Convenience function for basic vault search."""
    service = VaultSearchService(db)
    criteria = SearchCriteria(
        query=query,
        item_type=item_type,
        related_incident_id=incident_id,
        date_from=date_from,
        date_to=date_to,
        timeline_mode=timeline_mode,
        limit=limit,
    )
    return await service.search(user_id, criteria)
