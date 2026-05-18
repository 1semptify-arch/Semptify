"""
Auto Mode Orchestrator
======================

Coordinates all automated analyses for full auto mode:
- Timeline generation
- Calendar creation
- Complaint identification
- Rights assessment
- Legal missteps detection

Runs automatically on document upload when auto mode is enabled.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.event_bus import event_bus, EventType
from app.services.timeline_builder import TimelineBuilder
from app.services.calendar_service import CalendarService
from app.services.legal_analysis_engine import LegalAnalysisEngine
from app.services.complaint_wizard import ComplaintWizardService
from app.services.proactive_tactics import ProactiveTacticsEngine
from app.services.auto_mode_summary_service import AutoModeSummaryService

logger = logging.getLogger(__name__)


class AutoModeOrchestrator:
    """
    Orchestrates all automated analyses in full auto mode.
    """

    def __init__(self):
        self.timeline_builder = TimelineBuilder()
        self.calendar_service = CalendarService()
        self.legal_engine = LegalAnalysisEngine()
        self.complaint_wizard = ComplaintWizardService()
        self.tactics_engine = ProactiveTacticsEngine()
        self.summary_service = AutoModeSummaryService()

    async def run_full_auto_analysis(
        self,
        doc_id: str,
        user_id: str,
        document_content: str,
        document_metadata: Dict[str, Any],
        db_session: Any = None,
        filename: str = "document"
    ) -> Dict[str, Any]:
        """
        Run complete automated analysis on a document with full summary and recommendations.
        """
        logger.info(f"Starting full auto analysis for doc {doc_id}, user {user_id}")

        results = {
            'doc_id': doc_id,
            'user_id': user_id,
            'filename': filename,
            'timeline_events': [],
            'calendar_events': [],
            'complaints': [],
            'rights_assessment': {},
            'legal_missteps': [],
            'proactive_tactics': [],
            'analysis_timestamp': datetime.now().isoformat(),
            'summary': None,
            'status': 'processing'
        }

        try:
            # 1. Build timeline
            try:
                timeline_result = await self.timeline_builder.build_from_text(
                    document_content, document_id=doc_id
                )
                results['timeline_events'] = [event.to_dict() for event in timeline_result.events] if hasattr(timeline_result, 'events') else []
            except Exception as e:
                logger.warning(f"Timeline build error: {e}")
                results['timeline_events'] = []

            # 2. Generate calendar events
            try:
                calendar_events = await self.calendar_service.generate_events_from_timeline(
                    results['timeline_events']
                )
                results['calendar_events'] = [event.__dict__ for event in calendar_events] if calendar_events else []
            except Exception as e:
                logger.warning(f"Calendar generation error: {e}")
                results['calendar_events'] = []

            # 3. Legal analysis for rights and missteps
            try:
                case_data = {
                    'documents': {doc_id: {'full_text': document_content, **document_metadata}},
                    'issues': {}
                }
                legal_assessment = self.legal_engine.assess_legal_merit(case_data)
                if legal_assessment:
                    results['rights_assessment'] = {
                        'strengths': getattr(legal_assessment, 'strengths', []),
                        'weaknesses': getattr(legal_assessment, 'weaknesses', []),
                        'critical_issues': getattr(legal_assessment, 'critical_issues', [])
                    }
                    results['legal_missteps'] = getattr(legal_assessment, 'critical_issues', [])
            except Exception as e:
                logger.warning(f"Legal analysis error: {e}")
                results['rights_assessment'] = {}
                results['legal_missteps'] = []

            # 4. Identify potential complaints
            try:
                complaint_keywords = self._extract_complaint_keywords(document_content)
                recommended_agencies = self.complaint_wizard.get_recommended_agencies(complaint_keywords)
                if asyncio.iscoroutine(recommended_agencies):
                    recommended_agencies = await recommended_agencies
                results['complaints'] = [{'agency': getattr(agency, 'name', str(agency)), 'type': str(getattr(agency, 'type', 'unknown'))} for agency in (recommended_agencies or [])]
            except Exception as e:
                logger.warning(f"Complaint analysis error: {e}")
                results['complaints'] = []

            # 5. Generate proactive tactics
            try:
                tactics = self.tactics_engine.run_decision_tree(
                    timeline_events=results['timeline_events']
                )
                if asyncio.iscoroutine(tactics):
                    tactics = await tactics
                results['proactive_tactics'] = [tactic.to_dict() if hasattr(tactic, 'to_dict') else tactic.__dict__ for tactic in (tactics or [])]
            except Exception as e:
                logger.warning(f"Tactics analysis error: {e}")
                results['proactive_tactics'] = []

            # 6. Generate comprehensive summary with recommended actions
            try:
                summary_result = await self.summary_service.generate_summary(
                    doc_id, filename, results
                )
                results['summary'] = summary_result.to_dict() if hasattr(summary_result, 'to_dict') else summary_result
            except Exception as e:
                logger.warning(f"Summary generation error: {e}")
                results['summary'] = None

            results['status'] = 'complete'

            # 7. Publish results via event bus
            try:
                await event_bus.publish(EventType.DOCUMENT_FULLY_PROCESSED, {
                    'doc_id': doc_id,
                    'user_id': user_id,
                    'results': results,
                    'summary': results.get('summary')
                })
            except Exception as e:
                logger.warning(f"Event publish error: {e}")

            logger.info(f"Completed full auto analysis for doc {doc_id}")

        except Exception as e:
            logger.error(f"Error in auto analysis for doc {doc_id}: {e}")
            results['error'] = str(e)

        return results

    async def get_auto_mode_status(self, user_id: str) -> bool:
        """Check if auto mode is enabled for user."""
        return True

    def _extract_complaint_keywords(self, text: str) -> List[str]:
        """Extract keywords that might indicate complaint-worthy issues."""
        keywords = []
        text_lower = text.lower()

        complaint_indicators = [
            'repair', 'maintenance', 'broken', 'leak', 'mold', 'pest',
            'heat', 'hot water', 'plumbing', 'electrical', 'safety',
            'code violation', 'uninhabitable', 'retaliation', 'discrimination',
            'harassment', 'illegal', 'violation', 'breach'
        ]

        for indicator in complaint_indicators:
            if indicator in text_lower:
                keywords.append(indicator)

        return keywords
