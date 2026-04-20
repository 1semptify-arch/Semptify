"""
Telemetry Hooks System — v1.0

Event emission layer for PageContract telemetry_events.
- Emits to console (dev)
- Emits to mesh workflows (production)
- Buffers for batching
- Respects user privacy settings
"""

from __future__ import annotations

import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum, auto
from contextlib import contextmanager

# Setup logger
logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Priority levels for telemetry events."""
    CRITICAL = auto()   # User action affecting legal rights
    HIGH = auto()       # Important workflow step
    MEDIUM = auto()     # Standard interaction
    LOW = auto()        # Diagnostic/debug


@dataclass(frozen=True)
class TelemetryEvent:
    """
    Immutable telemetry event structure.
    All events include: timestamp, page_id, event_type, session_id, metadata.
    """
    event_type: str
    page_id: str
    session_id: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for transmission/storage."""
        return {
            "event_type": self.event_type,
            "page_id": self.page_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "priority": self.priority.name,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)


# Event type → Priority mapping (from PageContracts)
EVENT_PRIORITIES: Dict[str, EventPriority] = {
    # Critical: Rights-affecting actions
    "eviction_answer_load": EventPriority.CRITICAL,
    "answer_form_generated": EventPriority.CRITICAL,
    "counterclaim_added": EventPriority.CRITICAL,
    "court_packet_load": EventPriority.CRITICAL,
    "packet_generated": EventPriority.CRITICAL,
    "crisis_intake_load": EventPriority.CRITICAL,
    "emergency_resource_accessed": EventPriority.CRITICAL,
    "hotline_connected": EventPriority.CRITICAL,
    "evidence_indexed": EventPriority.CRITICAL,
    "answer_downloaded": EventPriority.CRITICAL,
    "defense_selected": EventPriority.CRITICAL,
    "packet_downloaded": EventPriority.CRITICAL,
    
    # High: Important workflow steps
    "dashboard_load": EventPriority.HIGH,
    "document_upload_started": EventPriority.HIGH,
    "vault_upload_complete": EventPriority.HIGH,
    "oauth_completed": EventPriority.HIGH,
    "storage_connected": EventPriority.HIGH,
    "talking_points_generated": EventPriority.HIGH,
    "form_added_to_packet": EventPriority.HIGH,
    "professional_workspace_load": EventPriority.HIGH,
    "case_opened": EventPriority.HIGH,
    "action_generated": EventPriority.HIGH,
    "admin_dashboard_load": EventPriority.HIGH,
    "functionx_set_executed": EventPriority.HIGH,
    "vault_upload_started": EventPriority.HIGH,
    "certificate_generated": EventPriority.HIGH,
    "mesh_workflow_triggered": EventPriority.HIGH,
    "advocate_escalation": EventPriority.HIGH,
    "document_downloaded": EventPriority.HIGH,
    "role_selected": EventPriority.HIGH,
    "process_start_clicked": EventPriority.HIGH,
    "storage_connect_clicked": EventPriority.HIGH,
    "config_change_saved": EventPriority.HIGH,
    "deadline_viewed": EventPriority.HIGH,
    "timeline_exported": EventPriority.HIGH,
    "hearing_joined": EventPriority.HIGH,
    "document_shared_in_hearing": EventPriority.HIGH,
    "motion_drafted": EventPriority.HIGH,
    "motion_filed": EventPriority.HIGH,
    "analysis_memo_generated": EventPriority.HIGH,
    
    # Medium: Standard interactions
    "tenant_dashboard_load": EventPriority.MEDIUM,
    "quick_action_clicked": EventPriority.MEDIUM,
    "research_query_submitted": EventPriority.MEDIUM,
    "export_initiated": EventPriority.MEDIUM,
    "kpi_dashboard_viewed": EventPriority.MEDIUM,
    "contract_health_checked": EventPriority.MEDIUM,
    "user_management_action": EventPriority.MEDIUM,
    "privileged_note_created": EventPriority.MEDIUM,
    "court_filing_generated": EventPriority.MEDIUM,
    "conflict_check_run": EventPriority.MEDIUM,
    "legal_research_query": EventPriority.MEDIUM,
    "functionx_set_created": EventPriority.MEDIUM,
    "functionx_set_viewed": EventPriority.MEDIUM,
    "case_summary_expanded": EventPriority.MEDIUM,
    "document_shared": EventPriority.MEDIUM,
    "overlay_viewed": EventPriority.MEDIUM,
    "vault_download": EventPriority.MEDIUM,
    "crisis_type_selected": EventPriority.MEDIUM,
    "help_requested": EventPriority.MEDIUM,
    "case_action_completed": EventPriority.MEDIUM,
    "legal_aid_resource_opened": EventPriority.MEDIUM,
    "storage_status_set": EventPriority.MEDIUM,
    
    # Low: Diagnostic / Navigation
    "storage_setup_load": EventPriority.LOW,
    "documents_page_load": EventPriority.LOW,
    "vault_load": EventPriority.LOW,
    "welcome_page_load": EventPriority.LOW,
    "tenant_help_load": EventPriority.LOW,
    "tenant_help_returned": EventPriority.LOW,
    "emergency_help_clicked": EventPriority.LOW,
    "hotline_clicked": EventPriority.LOW,
    "legal_workspace_load": EventPriority.LOW,
    "hearing_prep_load": EventPriority.LOW,
    "evidence_checklist_completed": EventPriority.LOW,
    "virtual_hearing_tested": EventPriority.LOW,
    "prep_guide_downloaded": EventPriority.LOW,
    "provider_selected": EventPriority.LOW,
    "oauth_started": EventPriority.LOW,
    "functionx_workspace_load": EventPriority.LOW,
    "timeline_load": EventPriority.LOW,
    "event_expanded": EventPriority.LOW,
    "timeline_filtered": EventPriority.LOW,
    "calendar_load": EventPriority.LOW,
    "date_selected": EventPriority.LOW,
    "event_added": EventPriority.LOW,
    "document_viewer_load": EventPriority.LOW,
    "overlay_toggled": EventPriority.LOW,
    "document_printed": EventPriority.LOW,
    "zoom_court_load": EventPriority.LOW,
    "test_mode_started": EventPriority.LOW,
    "audio_test_completed": EventPriority.LOW,
    "motions_load": EventPriority.LOW,
    "motion_template_selected": EventPriority.LOW,
    "legal_analysis_load": EventPriority.LOW,
    "statute_searched": EventPriority.LOW,
    "precedent_checked": EventPriority.LOW,
}


class TelemetryEmitter:
    """
    Central event emitter for page telemetry.
    
    Features:
    - Async-safe emission
    - Batching for performance
    - Privacy filtering
    - Mesh integration
    """
    
    def __init__(self):
        self._handlers: List[Callable[[TelemetryEvent], None]] = []
        self._buffer: List[TelemetryEvent] = []
        self._buffer_size = 100
        self._privacy_mode = False  # If True, no events emitted
        self._enabled = True
    
    def add_handler(self, handler: Callable[[TelemetryEvent], None]) -> None:
        """Register a callback for event processing."""
        self._handlers.append(handler)
    
    def enable(self) -> None:
        """Enable emission globally."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable emission globally."""
        self._enabled = False
    
    def set_privacy_mode(self, enabled: bool) -> None:
        """Enable privacy mode (no events recorded)."""
        self._privacy_mode = enabled
    
    def emit(
        self,
        event_type: str,
        page_id: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: Optional[EventPriority] = None,
    ) -> Optional[TelemetryEvent]:
        """
        Emit a telemetry event.
        
        Returns the event if emitted, None if filtered/disabled.
        """
        if not self._enabled or self._privacy_mode:
            return None
        
        # Auto-detect priority from event type
        if priority is None:
            priority = EVENT_PRIORITIES.get(event_type, EventPriority.MEDIUM)
        
        event = TelemetryEvent(
            event_type=event_type,
            page_id=page_id,
            session_id=session_id,
            metadata=metadata or {},
            priority=priority,
        )
        
        # Buffer for batching
        self._buffer.append(event)
        
        # Immediate emit for critical events
        if priority == EventPriority.CRITICAL:
            self._flush_event(event)
        
        # Batch flush when buffer full
        if len(self._buffer) >= self._buffer_size:
            self.flush()
        
        return event
    
    def _flush_event(self, event: TelemetryEvent) -> None:
        """Send single event to all handlers."""
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"Telemetry handler failed: {e}")
    
    def flush(self) -> None:
        """Flush buffered events to handlers."""
        if not self._buffer:
            return
        
        batch = self._buffer[:]
        self._buffer.clear()
        
        for event in batch:
            self._flush_event(event)
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """Return current buffer statistics."""
        return {
            "buffered": len(self._buffer),
            "by_priority": {
                p.name: sum(1 for e in self._buffer if e.priority == p)
                for p in EventPriority
            }
        }


# Global emitter instance
EMITTER = TelemetryEmitter()


# =============================================================================
# HANDLERS
# =============================================================================

def console_handler(event: TelemetryEvent) -> None:
    """Log telemetry to console (development)."""
    emoji = {
        EventPriority.CRITICAL: "🚨",
        EventPriority.HIGH: "⚡",
        EventPriority.MEDIUM: "📊",
        EventPriority.LOW: "🔍",
    }.get(event.priority, "📊")
    
    logger.info(
        f"{emoji} [{event.priority.name}] {event.event_type} "
        f"on {event.page_id} (session: {event.session_id[:8]}...)"
    )


def json_handler(event: TelemetryEvent) -> None:
    """Output full JSON for external systems."""
    print(event.to_json(), flush=True)


def mesh_handler(event: TelemetryEvent) -> None:
    """
    Emit to Positronic Mesh for workflow triggering.
    Only high-priority and critical events.
    """
    if event.priority not in (EventPriority.HIGH, EventPriority.CRITICAL):
        return
    
    try:
        from app.core.positronic_mesh import (
            mesh_trigger_workflow,
            TELEMETRY_WORKFLOW_TRIGGERS,
        )
        
        # Only trigger if this event type has a workflow mapping
        if event.event_type in TELEMETRY_WORKFLOW_TRIGGERS:
            mesh_trigger_workflow(
                workflow_id=event.event_type,
                payload={
                    "trigger_event": event.event_type,
                    "page_id": event.page_id,
                    "session_id": event.session_id,
                    **event.metadata
                }
            )
    except ImportError:
        pass  # Mesh not available


# Register default handlers
EMITTER.add_handler(console_handler)


# =============================================================================
# PAGE-LEVEL API
# =============================================================================

class PageTelemetry:
    """
    Per-page telemetry interface.
    
    Usage:
        telemetry = PageTelemetry("dashboard", session_id)
        telemetry.emit("quick_action_clicked", {"action": "view_deadlines"})
    """
    
    def __init__(self, page_id: str, session_id: str, emitter: TelemetryEmitter = EMITTER):
        self.page_id = page_id
        self.session_id = session_id
        self._emitter = emitter
    
    def emit(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: Optional[EventPriority] = None,
    ) -> Optional[TelemetryEvent]:
        """Emit event for this page."""
        return self._emitter.emit(
            event_type=event_type,
            page_id=self.page_id,
            session_id=self.session_id,
            metadata=metadata,
            priority=priority,
        )
    
    @contextmanager
    def timed_event(self, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for timing operations."""
        start = time.time()
        try:
            yield self
        finally:
            duration = time.time() - start
            self.emit(
                event_type=event_type,
                metadata={**(metadata or {}), "duration_ms": int(duration * 1000)},
            )
    
    def page_load(self, extra_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Convenience: emit standard page load event."""
        self.emit(
            event_type=f"{self.page_id}_load",
            metadata=extra_metadata,
        )


# =============================================================================
# VALIDATION
# =============================================================================

def validate_event_types() -> Dict[str, List[str]]:
    """
    Validate that all event types in PageContracts have priority mappings.
    Returns missing events by page.
    """
    try:
        from app.core.page_contracts import PAGE_CONTRACTS
    except ImportError:
        # Handle standalone execution
        import sys
        sys.path.insert(0, r"c:\Semptify\Semptify-FastAPI")
        from app.core.page_contracts import PAGE_CONTRACTS
    
    missing: Dict[str, List[str]] = {}
    
    for page_id, contract in PAGE_CONTRACTS.items():
        page_missing = [
            event for event in contract.telemetry_events
            if event not in EVENT_PRIORITIES
        ]
        if page_missing:
            missing[page_id] = page_missing
    
    return missing


# =============================================================================
# CLI / DEBUG
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Add handlers for full output
    EMITTER.add_handler(json_handler)
    
    # Test emission
    print("=== Telemetry System Test ===", file=sys.stderr)
    
    telemetry = PageTelemetry("dashboard", "test-session-12345")
    
    # Test basic emission
    telemetry.emit("quick_action_clicked", {"action": "view_deadlines"})
    
    # Test critical event
    EMITTER.emit(
        event_type="eviction_answer_load",
        page_id="eviction_answer",
        session_id="test-session-12345",
        metadata={"case_id": "C-2025-001"},
    )
    
    # Test timed event
    with telemetry.timed_event("api_call", {"endpoint": "/freeapi/courts/evictions"}):
        time.sleep(0.01)  # Simulate work
    
    # Flush and show stats
    EMITTER.flush()
    stats = EMITTER.get_buffer_stats()
    
    print(f"\n=== Stats ===", file=sys.stderr)
    print(f"Buffered: {stats['buffered']}", file=sys.stderr)
    
    # Show missing priority mappings
    missing = validate_event_types()
    if missing:
        print(f"\n=== Missing Priority Mappings ({len(missing)} pages) ===", file=sys.stderr)
        for page_id, events in missing.items():
            print(f"  {page_id}: {events}", file=sys.stderr)
    else:
        print("\n✅ All contract events have priority mappings", file=sys.stderr)
