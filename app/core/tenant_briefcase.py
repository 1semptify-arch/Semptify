"""
Tenant Briefcase - Persistent Tenant Data Object

A unified, lightweight data object available on every tenant page.
Combines vault, timeline, journal, and inbox into one accessible structure.

Design: HYBRID (lightweight summaries + smart methods)
- Fast load (~100ms)
- ~10KB memory footprint
- Lazy-load details on demand
- Template-friendly properties

Usage in templates:
    {{ briefcase.vault.total_documents }}
    {{ briefcase.next_deadline.title }}
    {{ briefcase.needs_attention }}
    
Usage in Python:
    briefcase = await get_tenant_briefcase(user_id)
    if briefcase.has_urgent_items:
        urgent = briefcase.get_urgent_items()
"""

import logging
from app.core.utc import utc_now
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Summary Data Classes (lightweight)
# =============================================================================

@dataclass
class VaultSummary:
    """Lightweight vault summary for briefcase."""
    total_documents: int = 0
    recent_documents: int = 0  # This month
    has_documents: bool = False
    by_type: Dict[str, int] = field(default_factory=dict)
    documents: List[Dict[str, Any]] = field(default_factory=list)  # Last 10 only
    storage_used_mb: float = 0.0
    
    @property
    def primary_type(self) -> str:
        """Most common document type."""
        if not self.by_type:
            return "none"
        return max(self.by_type.items(), key=lambda x: x[1])[0]


@dataclass
class TimelineEvent:
    """Single timeline event summary."""
    id: str
    event_type: str  # document_upload, deadline, court_date, notice_received, etc.
    title: str
    date: Optional[str] = None  # ISO format
    days_until: Optional[int] = None
    is_urgent: bool = False
    source_doc_id: Optional[str] = None
    icon: str = "📅"


@dataclass
class TimelineSummary:
    """Lightweight timeline summary."""
    total_events: int = 0
    events_this_month: int = 0
    has_timeline: bool = False
    next_deadline: Optional[TimelineEvent] = None
    urgent_events: List[TimelineEvent] = field(default_factory=list)
    recent_events: List[TimelineEvent] = field(default_factory=list)  # Last 5
    
    @property
    def has_upcoming_deadline(self) -> bool:
        return self.next_deadline is not None and self.next_deadline.days_until is not None


@dataclass
class JournalEntry:
    """Single journal entry summary."""
    id: str
    entry_type: str  # capture, note, conversation, etc.
    description: str
    created_at: str
    is_urgent: bool = False
    has_attachments: bool = False
    attachment_count: int = 0
    icon: str = "📝"


@dataclass
class JournalSummary:
    """Lightweight journal summary."""
    total_entries: int = 0
    entries_this_month: int = 0
    has_journal: bool = False
    urgent_entries: int = 0
    recent_entries: List[JournalEntry] = field(default_factory=list)  # Last 5


@dataclass
class Notification:
    """Single notification summary."""
    id: str
    notification_type: str  # document, deadline, system, alert
    title: str
    message: str
    created_at: str
    is_read: bool = False
    is_urgent: bool = False
    action_url: Optional[str] = None
    action_text: str = "View"
    icon: str = "📬"


@dataclass
class InboxSummary:
    """Lightweight inbox summary."""
    total_notifications: int = 0
    unread_count: int = 0
    urgent_count: int = 0
    has_notifications: bool = False
    latest_notification: Optional[Notification] = None


@dataclass
class QuickAction:
    """Suggested next action for tenant."""
    action_id: str
    title: str
    description: str
    priority: int  # 1 = highest
    icon: str
    url: str
    reason: str  # Why this action is suggested


@dataclass
class ActionSummary:
    """Available and suggested actions."""
    suggested_next: Optional[QuickAction] = None
    available_actions: List[QuickAction] = field(default_factory=list)
    completion_percentage: int = 0  # Case progress 0-100


# =============================================================================
# Main Briefcase Class
# =============================================================================

@dataclass
class TenantBriefcase:
    """
    Unified tenant data object - available on every tenant page.
    
    Combines summaries from all tenant subsystems:
    - Vault (documents)
    - Timeline (events, deadlines)
    - Journal (captures, notes)
    - Inbox (notifications)
    - Actions (next steps, progress)
    
    All fields are lightweight summaries. Use methods to fetch details.
    """
    user_id: str
    user_name: Optional[str] = None
    
    # Subsystem summaries
    vault: VaultSummary = field(default_factory=VaultSummary)
    timeline: TimelineSummary = field(default_factory=TimelineSummary)
    journal: JournalSummary = field(default_factory=JournalSummary)
    inbox: InboxSummary = field(default_factory=InboxSummary)
    actions: ActionSummary = field(default_factory=ActionSummary)
    
    # Metadata
    generated_at: str = field(default_factory=lambda: utc_now().isoformat())
    is_fresh: bool = True  # False if any subsystem failed to load
    
    # Freshness indicators
    freshness_score: float = 100.0  # Overall freshness score 0-100
    freshness_warnings: List[str] = field(default_factory=list)
    data_freshness_indicators: Dict[str, str] = field(default_factory=dict)
    
    # =============================================================================
    # Smart Properties (Template-friendly)
    # =============================================================================
    
    @property
    def has_any_data(self) -> bool:
        """True if tenant has any documents, entries, or events."""
        return (
            self.vault.has_documents or 
            self.timeline.has_timeline or 
            self.journal.has_journal
        )
    
    @property
    def is_new_tenant(self) -> bool:
        """True if tenant has no data yet (fresh onboarding)."""
        return not self.has_any_data
    
    @property
    def has_urgent_items(self) -> bool:
        """True if any urgent deadlines, notifications, or entries."""
        return (
            len(self.timeline.urgent_events) > 0 or
            self.journal.urgent_entries > 0 or
            self.inbox.urgent_count > 0
        )
    
    @property
    def needs_attention(self) -> bool:
        """True if tenant has unread notifications or upcoming deadlines."""
        return (
            self.inbox.unread_count > 0 or
            (self.timeline.next_deadline and self.timeline.next_deadline.days_until is not None and self.timeline.next_deadline.days_until <= 7)
        )
    
    @property
    def next_deadline(self) -> Optional[TimelineEvent]:
        """Most urgent upcoming deadline (or None)."""
        return self.timeline.next_deadline
    
    @property
    def document_count(self) -> int:
        """Total documents in vault."""
        return self.vault.total_documents
    
    @property
    def activity_count(self) -> int:
        """Total activity (docs + entries + events)."""
        return (
            self.vault.total_documents +
            self.journal.total_entries +
            self.timeline.total_events
        )
    
    @property
    def case_progress(self) -> int:
        """Percentage of case completion (0-100)."""
        return self.actions.completion_percentage
    
    @property
    def has_freshness_issues(self) -> bool:
        """True if any data freshness issues detected."""
        return (
            self.freshness_score < 90.0 or
            len(self.freshness_warnings) > 0 or
            any(status == "stale" for status in self.data_freshness_indicators.values())
        )
    
    @property
    def freshness_status(self) -> str:
        """Overall freshness status for UI display."""
        if self.freshness_score >= 95:
            return "excellent"
        elif self.freshness_score >= 85:
            return "good"
        elif self.freshness_score >= 70:
            return "fair"
        else:
            return "poor"
    
    @property
    def freshness_color(self) -> str:
        """Color indicator for freshness status."""
        if self.freshness_score >= 95:
            return "#10b981"  # green
        elif self.freshness_score >= 85:
            return "#3b82f6"  # blue
        elif self.freshness_score >= 70:
            return "#f59e0b"  # amber
        else:
            return "#ef4444"  # red
    
    # =============================================================================
    # Smart Methods (Lazy-load details)
    # =============================================================================
    
    def get_urgent_items(self, max_items: int = 5) -> List[Dict[str, Any]]:
        """
        Get all urgent items sorted by priority.
        Combines timeline, journal, and inbox urgent items.
        """
        items = []
        
        # Timeline urgent events
        for event in self.timeline.urgent_events[:max_items]:
            items.append({
                "type": "deadline",
                "id": event.id,
                "title": event.title,
                "date": event.date,
                "days_until": event.days_until,
                "icon": event.icon,
                "priority": 1 if event.days_until is not None and event.days_until <= 3 else 2,
            })
        
        # Journal urgent entries
        for entry in self.journal.recent_entries:
            if entry.is_urgent:
                items.append({
                    "type": "journal",
                    "id": entry.id,
                    "title": entry.description[:50] + "..." if len(entry.description) > 50 else entry.description,
                    "date": entry.created_at,
                    "icon": entry.icon,
                    "priority": 2,
                })
        
        # Inbox urgent notifications
        if self.inbox.latest_notification and self.inbox.latest_notification.is_urgent:
            n = self.inbox.latest_notification
            items.append({
                "type": "notification",
                "id": n.id,
                "title": n.title,
                "date": n.created_at,
                "icon": n.icon,
                "priority": 1,
            })
        
        # Sort by priority
        items.sort(key=lambda x: x["priority"])
        return items[:max_items]
    
    def has_deadline_approaching(self, days: int = 7) -> bool:
        """Check if any deadline is within N days."""
        if not self.timeline.next_deadline:
            return False
        if self.timeline.next_deadline.days_until is None:
            return False
        return self.timeline.next_deadline.days_until <= days
    
    def get_recent_activity(self, max_items: int = 10) -> List[Dict[str, Any]]:
        """Get mixed recent activity from all sources."""
        activities = []
        
        # Vault uploads
        for doc in self.vault.documents[:max_items]:
            activities.append({
                "type": "document",
                "id": doc.get("id", "unknown"),
                "title": doc.get("title", "Unknown document"),
                "date": doc.get("uploaded_at"),
                "icon": "📄",
                "description": f"Uploaded: {doc.get('title', 'Document')}",
            })
        
        # Journal entries
        for entry in self.journal.recent_entries[:max_items]:
            activities.append({
                "type": "journal",
                "id": entry.id,
                "title": entry.description[:40] + "..." if len(entry.description) > 40 else entry.description,
                "date": entry.created_at,
                "icon": entry.icon,
                "description": entry.description,
            })
        
        # Timeline events
        for event in self.timeline.recent_events[:max_items]:
            activities.append({
                "type": "event",
                "id": event.id,
                "title": event.title,
                "date": event.date,
                "icon": event.icon,
                "description": event.title,
            })
        
        # Sort by date (newest first) - approximate since dates may be ISO strings
        activities.sort(key=lambda x: x.get("date") or "", reverse=True)
        return activities[:max_items]
    
    def update_freshness_indicators(self) -> None:
        """Update freshness indicators from data freshness manager."""
        try:
            from app.core.data_freshness_manager import data_freshness_manager, FreshnessStatus
        except ImportError:
            logger.warning("Data freshness manager not available")
            return
        
        # Check key data freshness
        indicators = {}
        warnings = []
        
        # Legal content freshness
        legal_freshness = data_freshness_manager.check_freshness("legal_content")
        indicators["legal_content"] = legal_freshness.value
        if legal_freshness != FreshnessStatus.FRESH:
            warnings.append("Legal content may be outdated")
        
        # Court forms freshness
        forms_freshness = data_freshness_manager.check_freshness("court_forms")
        indicators["court_forms"] = forms_freshness.value
        if forms_freshness != FreshnessStatus.FRESH:
            warnings.append("Court form requirements may be outdated")
        
        # Deadline rules freshness
        deadlines_freshness = data_freshness_manager.check_freshness("deadline_rules")
        indicators["deadline_rules"] = deadlines_freshness.value
        if deadlines_freshness != FreshnessStatus.FRESH:
            warnings.append("Deadline calculation rules may be outdated")
        
        # Update briefcase
        self.data_freshness_indicators = indicators
        self.freshness_warnings = warnings
        
        # Calculate overall score
        fresh_count = sum(1 for status in indicators.values() if status == FreshnessStatus.FRESH.value)
        self.freshness_score = (fresh_count / len(indicators)) * 100 if indicators else 100.0
    
    def to_template_context(self) -> Dict[str, Any]:
        """Convert to flat dict for template rendering."""
        return {
            # Direct briefcase access
            "briefcase": self,
            
            # Flat shortcuts (for template convenience)
            "vault": self.vault,
            "timeline": self.timeline,
            "journal": self.journal,
            "inbox": self.inbox,
            "actions": self.actions,
            
            # Common quick accessors
            "user_name": self.user_name,
            "document_count": self.document_count,
            "activity_count": self.activity_count,
            "case_progress": self.case_progress,
            "has_any_data": self.has_any_data,
            "is_new_tenant": self.is_new_tenant,
            "has_urgent_items": self.has_urgent_items,
            "needs_attention": self.needs_attention,
            "next_deadline": self.next_deadline,
            
            # Freshness indicators
            "freshness_score": self.freshness_score,
            "freshness_status": self.freshness_status,
            "freshness_color": self.freshness_color,
            "has_freshness_issues": self.has_freshness_issues,
            "freshness_warnings": self.freshness_warnings,
            "data_freshness_indicators": self.data_freshness_indicators,
            
            # Pre-computed lists
            "urgent_items": self.get_urgent_items(),
            "recent_activity": self.get_recent_activity(),
        }


# =============================================================================
# Factory Function
# =============================================================================

async def get_tenant_briefcase(user_id: str, user_name: Optional[str] = None) -> TenantBriefcase:
    """
    Build a complete TenantBriefcase for the given user.
    
    This is the main entry point - call this from every tenant route
    to get unified tenant data.
    
    Args:
        user_id: The tenant's user ID
        user_name: Optional display name
        
    Returns:
        TenantBriefcase with all subsystem summaries
    """
    briefcase = TenantBriefcase(user_id=user_id, user_name=user_name)
    
    try:
        # Load vault summary
        vault_data = await _load_vault_summary(user_id)
        briefcase.vault = vault_data
    except Exception as e:
        logger.warning(f"Failed to load vault for {user_id}: {e}")
        briefcase.is_fresh = False
    
    try:
        # Load timeline from vault documents
        timeline_data = await _load_timeline_summary(user_id, briefcase.vault)
        briefcase.timeline = timeline_data
    except Exception as e:
        logger.warning(f"Failed to load timeline for {user_id}: {e}")
        briefcase.is_fresh = False
    
    try:
        # Load journal (captures/entries)
        journal_data = await _load_journal_summary(user_id, briefcase.vault)
        briefcase.journal = journal_data
    except Exception as e:
        logger.warning(f"Failed to load journal for {user_id}: {e}")
        briefcase.is_fresh = False
    
    try:
        # Generate inbox from state changes
        inbox_data = await _load_inbox_summary(user_id, briefcase)
        briefcase.inbox = inbox_data
    except Exception as e:
        logger.warning(f"Failed to load inbox for {user_id}: {e}")
        briefcase.is_fresh = False
    
    try:
        # Compute suggested actions
        action_data = await _load_action_summary(user_id, briefcase)
        briefcase.actions = action_data
    except Exception as e:
        logger.warning(f"Failed to load actions for {user_id}: {e}")
        briefcase.is_fresh = False
    
    # Update freshness indicators (non-blocking)
    try:
        briefcase.update_freshness_indicators()
    except Exception as e:
        logger.warning(f"Failed to update freshness indicators for {user_id}: {e}")
    
    return briefcase


# =============================================================================
# Internal Data Loaders (subsystem specific)
# =============================================================================

async def _load_vault_summary(user_id: str) -> VaultSummary:
    """Load vault documents and compute summary."""
    try:
        from app.services.document_pipeline import get_document_pipeline
        from app.services.vault_upload_service import get_vault_service
        
        # Try pipeline first (has rich metadata)
        pipeline = get_document_pipeline()
        docs = pipeline.get_user_documents(user_id)
        summary = pipeline.get_summary(user_id) if hasattr(pipeline, 'get_summary') else {}
        
        # Format last 10 documents
        doc_list = []
        for doc in docs[-10:]:
            doc_list.append({
                "id": doc.id,
                "title": doc.title or doc.filename,
                "filename": doc.filename,
                "doc_type": doc.doc_type.value if doc.doc_type else "unknown",
                "status": doc.status.value if doc.status else "unknown",
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "has_timeline": bool(doc.key_dates),
                "is_certified": getattr(doc, 'registry_id', None) is not None,
            })
        
        # Count recent (this month)
        now = utc_now()
        recent = len([
            d for d in docs 
            if d.uploaded_at and (now - d.uploaded_at).days < 30
        ])
        
        return VaultSummary(
            total_documents=len(docs),
            recent_documents=recent,
            has_documents=len(docs) > 0,
            by_type=summary.get("by_type", {}),
            documents=doc_list,
            storage_used_mb=sum(d.file_size for d in docs if hasattr(d, 'file_size')) / (1024 * 1024),
        )
    except Exception as e:
        logger.warning(f"Vault summary load failed: {e}")
        return VaultSummary()


async def _load_timeline_summary(user_id: str, vault: VaultSummary) -> TimelineSummary:
    """Extract timeline events from vault documents."""
    events = []
    urgent_events = []
    next_deadline = None
    
    # Extract dates from vault documents
    for doc in vault.documents:
        if doc.get("uploaded_at"):
            events.append(TimelineEvent(
                id=f"upload_{doc['id']}",
                event_type="document_upload",
                title=f"Uploaded: {doc['title']}",
                date=doc["uploaded_at"],
                icon="📄",
            ))
        
        # Check for document dates (from key_dates in full doc)
        if doc.get("has_timeline"):
            events.append(TimelineEvent(
                id=f"docdate_{doc['id']}",
                event_type="document_date",
                title=f"Date in: {doc['title']}",
                icon="📅",
            ))
    
    # Load real timeline events from DB
    try:
        from app.core.database import get_db_session
        from app.models.models import TimelineEvent as TimelineEventModel
        from sqlalchemy import select as _sel
        async with get_db_session() as _db:
            result = await _db.execute(
                _sel(TimelineEventModel)
                .where(TimelineEventModel.user_id == user_id)
                .order_by(TimelineEventModel.event_date.asc())
            )
            for te in result.scalars().all():
                date_val = te.event_date.isoformat() if te.event_date else None
                events.append(TimelineEvent(
                    id=str(te.id),
                    event_type=te.event_type or "event",
                    title=te.title or te.event_type or "Event",
                    date=date_val,
                    icon="📅",
                ))
    except Exception as _e:
        logger.warning("Timeline DB load failed: %s", _e)

    # Find next deadline
    today = utc_now().date()
    for event in events:
        if event.date:
            try:
                event_date = datetime.fromisoformat(event.date.replace('Z', '+00:00')).date()
                days = (event_date - today).days
                if days >= 0:
                    event.days_until = days
                    if days <= 14:
                        event.is_urgent = True
                        urgent_events.append(event)
                    if not next_deadline or (next_deadline.days_until is not None and days < next_deadline.days_until):
                        next_deadline = event
            except ValueError:
                pass
    
    return TimelineSummary(
        total_events=len(events),
        events_this_month=len([e for e in events if e.date and "2026-04" in e.date]),  # Simplistic
        has_timeline=len(events) > 0,
        next_deadline=next_deadline,
        urgent_events=urgent_events[:3],
        recent_events=sorted(events, key=lambda x: x.date or "", reverse=True)[:5],
    )


async def _load_journal_summary(user_id: str, vault: VaultSummary) -> JournalSummary:
    """Load journal entries (captures)."""
    entries = []
    try:
        from app.core.database import get_db_session
        from app.models.models import Document as DocumentModel
        from sqlalchemy import select as _sel
        async with get_db_session() as _db:
            result = await _db.execute(
                _sel(DocumentModel)
                .where(DocumentModel.user_id == user_id)
                .order_by(DocumentModel.uploaded_at.desc())
                .limit(50)
            )
            for doc in result.scalars().all():
                is_urgent = (doc.document_type or "") in (
                    "eviction_notice", "court_order", "lease_termination", "court_summons", "court_complaint"
                )
                entries.append(JournalEntry(
                    id=str(doc.id),
                    entry_type="document_upload",
                    description=f"Document: {doc.original_filename or doc.filename}",
                    created_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
                    is_urgent=is_urgent,
                    has_attachments=True,
                    attachment_count=1,
                ))
        # fall through to vault fallback below if nothing loaded
    except Exception as _e:
        logger.warning("Journal DB load failed: %s", _e)

    if not entries:
        for doc in vault.documents:
            is_urgent = doc.get("doc_type") in ["eviction_notice", "court_order", "lease_termination"]
            entries.append(JournalEntry(
                id=doc["id"],
                entry_type="document_upload",
                description=f"Document: {doc['title']}",
                created_at=doc.get("uploaded_at", ""),
                is_urgent=is_urgent,
                has_attachments=True,
                attachment_count=1,
            ))
    
    urgent_count = len([e for e in entries if e.is_urgent])
    
    return JournalSummary(
        total_entries=len(entries),
        entries_this_month=vault.recent_documents,
        has_journal=len(entries) > 0,
        urgent_entries=urgent_count,
        recent_entries=sorted(entries, key=lambda x: x.created_at, reverse=True)[:5],
    )


async def _load_inbox_summary(user_id: str, briefcase: TenantBriefcase) -> InboxSummary:
    """Generate inbox notifications from briefcase state."""
    notifications = []
    
    # Notification: New documents this month
    if briefcase.vault.recent_documents > 0:
        notifications.append(Notification(
            id="vault_update",
            notification_type="document",
            title=f"{briefcase.vault.recent_documents} new document(s)",
            message="Your vault has been updated with new uploads.",
            created_at=utc_now().isoformat(),
            is_read=False,
            is_urgent=False,
            action_url="/tenant/journal",
            action_text="View",
        ))
    
    # Notification: Upcoming deadline
    if briefcase.timeline.next_deadline and briefcase.timeline.next_deadline.days_until is not None:
        days = briefcase.timeline.next_deadline.days_until
        if days <= 7:
            notifications.append(Notification(
                id="deadline_urgent",
                notification_type="deadline",
                title=f"Deadline in {days} days!",
                message=briefcase.timeline.next_deadline.title,
                created_at=utc_now().isoformat(),
                is_read=False,
                is_urgent=True,
                action_url="/timeline",
                action_text="View Timeline",
            ))
    
    # Notification: Urgent journal entries
    if briefcase.journal.urgent_entries > 0:
        notifications.append(Notification(
            id="urgent_journal",
            notification_type="alert",
            title=f"{briefcase.journal.urgent_entries} urgent item(s)",
            message="Documents requiring immediate attention",
            created_at=utc_now().isoformat(),
            is_read=False,
            is_urgent=True,
            action_url="/tenant/journal",
            action_text="Review",
        ))
    
    unread = len([n for n in notifications if not n.is_read])
    urgent = len([n for n in notifications if n.is_urgent])
    
    return InboxSummary(
        total_notifications=len(notifications),
        unread_count=unread,
        urgent_count=urgent,
        has_notifications=len(notifications) > 0,
        latest_notification=notifications[0] if notifications else None,
    )


async def _load_action_summary(user_id: str, briefcase: TenantBriefcase) -> ActionSummary:
    """Compute suggested next actions based on tenant state."""
    actions = []
    suggested = None
    
    # Determine progress based on data volume
    progress = 0
    if briefcase.vault.has_documents:
        progress += 30
    if briefcase.timeline.has_timeline:
        progress += 20
    if briefcase.journal.has_journal:
        progress += 20
    if briefcase.inbox.urgent_count == 0:
        progress += 30
    
    # Suggest actions based on state
    if not briefcase.vault.has_documents:
        suggested = QuickAction(
            action_id="upload_first",
            title="Upload Your First Document",
            description="Start by uploading a lease, notice, or any relevant document",
            priority=1,
            icon="📄",
            url="/tenant/capture",
            reason="No documents in your vault yet",
        )
        actions.append(suggested)
    
    if briefcase.timeline.next_deadline and briefcase.timeline.next_deadline.days_until is not None:
        if briefcase.timeline.next_deadline.days_until <= 7:
            deadline_action = QuickAction(
                action_id="review_deadline",
                title="Review Upcoming Deadline",
                description=f"You have a deadline in {briefcase.timeline.next_deadline.days_until} days",
                priority=1 if briefcase.timeline.next_deadline.days_until <= 3 else 2,
                icon="⏰",
                url="/timeline",
                reason="Urgent deadline approaching",
            )
            if not suggested:
                suggested = deadline_action
            actions.append(deadline_action)
    
    if briefcase.inbox.urgent_count > 0:
        actions.append(QuickAction(
            action_id="check_inbox",
            title="Check Urgent Notifications",
            description=f"{briefcase.inbox.urgent_count} item(s) need attention",
            priority=1,
            icon="📬",
            url="/tenant/inbox",
            reason="Unread urgent notifications",
        ))
    
    # Always suggest capture
    actions.append(QuickAction(
        action_id="quick_capture",
        title="Quick Capture",
        description="Record something that just happened",
        priority=3,
        icon="⚡",
        url="/tenant/capture",
        reason="Keep your record up to date",
    ))
    
    return ActionSummary(
        suggested_next=suggested,
        available_actions=actions,
        completion_percentage=progress,
    )
