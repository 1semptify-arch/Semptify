"""
Calendar Service for Semptify
Generates calendar events from timeline and documents
"""

import logging
import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CalendarEventType(str, Enum):
    """Types of calendar events"""
    COURT_HEARING = "court_hearing"
    NOTICE_DEADLINE = "notice_deadline"
    PAYMENT_DUE = "payment_due"
    DOCUMENT_DEADLINE = "document_deadline"
    INSPECTION = "inspection"
    MEDIATION = "mediation"
    OTHER = "other"


@dataclass
class CalendarEvent:
    """Represents a calendar event"""
    title: str
    description: str
    start_date: date
    event_type: CalendarEventType
    reminders: List[int] = None  # reminders in minutes before event

    def __post_init__(self):
        if self.reminders is None:
            self.reminders = [1440]  # default 1 day


class CalendarService:
    """
    Generates calendar events from documents and timelines
    """

    def __init__(self):
        self.logger = logger

    async def generate_events_from_timeline(
        self,
        timeline_events: List[Dict[str, Any]]
    ) -> List[CalendarEvent]:
        """
        Generate calendar events from timeline events
        """
        events = []

        try:
            for event in timeline_events:
                if isinstance(event, dict):
                    event_data = event
                else:
                    event_data = event.to_dict() if hasattr(event, 'to_dict') else event.__dict__

                # Extract date
                event_date = self._extract_date(event_data)
                if not event_date:
                    continue

                # Create calendar event
                cal_event = self._create_calendar_event(event_data, event_date)
                if cal_event:
                    events.append(cal_event)

        except Exception as e:
            logger.warning(f"Error generating calendar events: {e}")

        return events

    def _extract_date(self, event_data: Dict[str, Any]) -> Optional[date]:
        """Extract date from event data"""
        date_formats = ['date', 'event_date', 'start_date', 'deadline', 'due_date']

        for field in date_formats:
            if field in event_data:
                value = event_data[field]
                if isinstance(value, date):
                    return value
                elif isinstance(value, datetime):
                    return value.date()
                elif isinstance(value, str):
                    try:
                        return datetime.strptime(value, '%Y-%m-%d').date()
                    except:
                        pass

        return None

    def _create_calendar_event(
        self,
        event_data: Dict[str, Any],
        event_date: date
    ) -> Optional[CalendarEvent]:
        """Create a calendar event from event data"""
        title = event_data.get('title', event_data.get('description', 'Event'))
        description = event_data.get('description', event_data.get('title', ''))
        event_type_str = event_data.get('type', event_data.get('event_type', 'other')).lower()

        # Map event type
        cal_type = CalendarEventType.OTHER
        if 'hearing' in event_type_str or 'court' in event_type_str:
            cal_type = CalendarEventType.COURT_HEARING
        elif 'deadline' in event_type_str or 'notice' in event_type_str:
            cal_type = CalendarEventType.NOTICE_DEADLINE
        elif 'payment' in event_type_str or 'due' in event_type_str:
            cal_type = CalendarEventType.PAYMENT_DUE
        elif 'document' in event_type_str:
            cal_type = CalendarEventType.DOCUMENT_DEADLINE
        elif 'inspection' in event_type_str:
            cal_type = CalendarEventType.INSPECTION
        elif 'mediation' in event_type_str:
            cal_type = CalendarEventType.MEDIATION

        # Set reminders
        if cal_type == CalendarEventType.COURT_HEARING:
            reminders = [1440, 60]  # 1 day, 1 hour
        elif cal_type == CalendarEventType.NOTICE_DEADLINE:
            reminders = [1440]  # 1 day
        elif cal_type == CalendarEventType.PAYMENT_DUE:
            reminders = [4320, 1440]  # 3 days, 1 day
        else:
            reminders = [1440]  # default 1 day

        return CalendarEvent(
            title=title,
            description=description,
            start_date=event_date,
            event_type=cal_type,
            reminders=reminders,
        )

    async def get_upcoming_events(
        self,
        events: List[CalendarEvent],
        days_ahead: int = 30
    ) -> List[CalendarEvent]:
        """Get upcoming events within specified days."""
        now = date.today()
        cutoff = now + timedelta(days=days_ahead)

        upcoming = []
        for event in events:
            if event.start_date >= now and event.start_date <= cutoff:
                upcoming.append(event)

        return sorted(upcoming, key=lambda x: x.start_date)
