"""
Semptify Timeline Extraction

Extracts dates and events from documents using overlay system.

Principles:
- Only reads from overlay (never touches original)
- Stores extracted events in user's cloud storage
- All processing happens client-side or in ephemeral memory
"""

import re
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum

from app.core.id_gen import make_id
from app.core.vault_paths import VAULT_TIMELINE, VAULT_TIMELINE_EVENTS_FILE, VAULT_TIMELINE_EVENTS_FILENAME


class EventType(Enum):
    """Types of timeline events."""
    NOTICE_RECEIVED = "notice_received"
    NOTICE_SENT = "notice_sent"
    COURT_DATE = "court_date"
    DEADLINE = "deadline"
    PAYMENT = "payment"
    REPAIR_REQUEST = "repair_request"
    REPAIR_COMPLETED = "repair_completed"
    MOVE_IN = "move_in"
    MOVE_OUT = "move_out"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"


@dataclass
class TimelineEvent:
    """A single event on the timeline."""
    event_id: str
    date: str  # ISO format date
    event_type: str
    title: str
    description: str
    source_document_id: str  # Which document this came from
    source_overlay_id: str  # Which overlay was used
    extracted_at: str
    confidence: float = 0.8  # 0.0 to 1.0
    verified: bool = False  # User has confirmed this event
    
    def to_dict(self) -> dict:
        return asdict(self)


class TimelineExtractor:
    """
    Extracts timeline events from documents using overlays.
    
    Uses regex patterns to find dates and contextual text.
    More sophisticated extraction can be added later (OCR, LLM, etc.)
    """
    
    # Date patterns (MM/DD/YYYY, MM-DD-YYYY, Month DD, YYYY, etc.)
    DATE_PATTERNS = [
        r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',  # 01/15/2024, 01-15-24
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
        r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
    ]
    
    # Event type keywords
    EVENT_KEYWORDS = {
        EventType.NOTICE_RECEIVED: [
            "notice", "received", "served", "delivered", "post", "posted",
            "14 day", "30 day", "3 day", "eviction notice", "pay or quit"
        ],
        EventType.COURT_DATE: [
            "court", "hearing", "trial", "unlawful detainer", "ud", 
            "small claims", "filing", "lawsuit", "summons"
        ],
        EventType.DEADLINE: [
            "deadline", "due", "must pay", "must respond", "expiration",
            "expires", "last day", "final date"
        ],
        EventType.PAYMENT: [
            "rent", "payment", "paid", "deposit", "security deposit",
            "late fee", "penalty"
        ],
        EventType.REPAIR_REQUEST: [
            "repair", "maintenance", "fix", "broken", "leak", "heat",
            "plumbing", "electrical", "request", "complaint"
        ],
        EventType.COMMUNICATION: [
            "email", "letter", "text", "message", "call", "conversation",
            "spoke", "discussed", "informed"
        ],
    }
    
    def __init__(self, overlay_manager):
        self.overlay_manager = overlay_manager
    
    async def extract_from_document(self, overlay_id: str, original_id: str) -> List[TimelineEvent]:
        """
        Extract timeline events from a document overlay.
        
        Args:
            overlay_id: ID of the overlay to process
            original_id: ID of the original document (for reference)
        
        Returns:
            List of TimelineEvent objects
        """
        # Get overlay metadata
        overlay = await self.overlay_manager.get_overlay(overlay_id)
        if not overlay:
            return []
        
        # Read document content from vault path (read-only, original stays immutable)
        try:
            content_bytes = await self.overlay_manager.storage.download_file(overlay.vault_path)
            content_text = self._extract_text_from_pdf(content_bytes)
        except Exception:
            # If we can't read the document, return empty
            return []
        
        events = []
        
        # Extract dates with context
        for date_match in self._find_dates(content_text):
            date_str = date_match['date']
            context = date_match['context']
            
            # Determine event type from context
            event_type = self._classify_event_type(context)
            
            # Create event
            event = TimelineEvent(
                event_id=make_id("evt"),
                date=date_str,
                event_type=event_type.value,
                title=self._generate_title(event_type, context),
                description=context[:200],  # First 200 chars as description
                source_document_id=original_id,
                source_overlay_id=overlay_id,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                confidence=0.7,  # Regex-based = moderate confidence
                verified=False
            )
            events.append(event)
        
        # Update overlay metadata with extracted events
        await self.overlay_manager.update_overlay(
            overlay_id,
            metadata={"extracted_dates": [e.date for e in events]},
        )
        
        return events
    
    def _find_dates(self, text: str) -> List[Dict[str, str]]:
        """Find dates in text with surrounding context."""
        dates = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in self.DATE_PATTERNS:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    # Get context (this line + 1 before + 1 after)
                    context_lines = []
                    if i > 0:
                        context_lines.append(lines[i-1])
                    context_lines.append(line)
                    if i < len(lines) - 1:
                        context_lines.append(lines[i+1])
                    
                    context = ' '.join(context_lines)
                    
                    # Normalize date to ISO format
                    date_str = self._normalize_date(match.group())
                    if date_str:
                        dates.append({
                            'date': date_str,
                            'context': context.strip()
                        })
        
        return dates
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Convert various date formats to ISO YYYY-MM-DD."""
        # TODO: Implement proper date normalization
        # For now, return as-is with current year if missing
        return date_str
    
    def _classify_event_type(self, context: str) -> EventType:
        """Determine event type from context keywords."""
        context_lower = context.lower()
        
        scores = {}
        for event_type, keywords in self.EVENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in context_lower)
            if score > 0:
                scores[event_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return EventType.UNKNOWN
    
    def _generate_title(self, event_type: EventType, context: str) -> str:
        """Generate a human-readable title for the event."""
        titles = {
            EventType.NOTICE_RECEIVED: "Notice Received",
            EventType.COURT_DATE: "Court Date",
            EventType.DEADLINE: "Deadline",
            EventType.PAYMENT: "Payment",
            EventType.REPAIR_REQUEST: "Repair Request",
            EventType.REPAIR_COMPLETED: "Repair Completed",
            EventType.COMMUNICATION: "Communication",
            EventType.UNKNOWN: "Event",
        }
        return titles.get(event_type, "Event")
    
    def _extract_text_from_pdf(self, content_bytes: bytes) -> str:
        """
        Extract text from PDF bytes using pdfplumber.
        """
        try:
            import pdfplumber
            import io
            
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return '\n'.join(text_parts)
        except Exception as e:
            # Fallback: try PyPDF2
            try:
                import PyPDF2
                import io
                
                reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or '')
                return '\n'.join(text_parts)
            except Exception:
                # If all extraction fails, return empty
                return ''


class TimelineStore:
    """
    Stores timeline events in user's cloud storage.
    
    Location: Semptify5.0/Vault/timeline/
    """
    
    TIMELINE_FOLDER = VAULT_TIMELINE
    EVENTS_FILE = VAULT_TIMELINE_EVENTS_FILE
    
    def __init__(self, storage_provider, access_token: str):
        self.storage = storage_provider
        self.token = access_token
    
    async def save_events(self, events: List[TimelineEvent]):
        """Save events to user's timeline storage."""
        # Load existing events
        existing = await self._load_events()
        
        # Merge new events (avoid duplicates by event_id)
        existing_ids = {e['event_id'] for e in existing}
        for event in events:
            if event.event_id not in existing_ids:
                existing.append(event.to_dict())
        
        # Sort by date
        existing.sort(key=lambda x: x['date'])
        
        # Save back to storage
        await self._save_events(existing)
    
    async def get_timeline(self) -> List[Dict[str, Any]]:
        """Get all timeline events for user."""
        return await self._load_events()
    
    async def _load_events(self) -> List[Dict[str, Any]]:
        """Load events from storage."""
        try:
            # Read events.json from user's timeline folder using download_file
            content = await self.storage.download_file(self.EVENTS_FILE)
            if content:
                return json.loads(content.decode('utf-8'))
            return []
        except Exception:
            # File doesn't exist or can't read - return empty
            return []
    
    async def _save_events(self, events: List[Dict[str, Any]]):
        """Save events to storage."""
        try:
            # Ensure timeline folder exists
            try:
                await self.storage.create_folder(self.TIMELINE_FOLDER)
            except Exception:
                pass  # Folder may already exist
            
            # Write events.json using upload_file
            events_json = json.dumps(events, indent=2)
            await self.storage.upload_file(
                file_content=events_json.encode('utf-8'),
                destination_path=self.TIMELINE_FOLDER,
                filename=VAULT_TIMELINE_EVENTS_FILENAME,
                mime_type="application/json",
            )
        except Exception as e:
            # Log but don't fail - timeline extraction is secondary to document storage
            import logging
            logging.getLogger(__name__).warning(f"Failed to save timeline events: {e}")


# =============================================================================
# Convenience Functions
# =============================================================================

async def extract_timeline_from_upload(document_id: str, overlay_id: str,
                                       provider: str, access_token: str):
    """
    Extract timeline from a newly uploaded document.
    
    Usage:
        events = await extract_timeline_from_upload(
            document_id="doc_123",
            overlay_id="ovl_doc_123_...",
            provider="google_drive",
            access_token="..."
        )
        # Events are auto-saved to user's timeline
    """
    from app.services.unified_overlay_manager import UnifiedOverlayManager
    from app.services.storage import get_provider

    storage = get_provider(provider, access_token=access_token)
    
    overlay_manager = UnifiedOverlayManager(storage, "system")
    extractor = TimelineExtractor(overlay_manager)
    
    # Extract events
    events = await extractor.extract_from_document(overlay_id, document_id)
    
    # Save to user's timeline
    timeline_store = TimelineStore(storage, access_token)
    await timeline_store.save_events(events)
    
    return events
