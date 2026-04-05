"""
Auto Mode Summary Service
=========================

Generates comprehensive summaries and actionable recommendations from automated analysis.
Creates progress reports with suggested actions for each document.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AnalysisSummary:
    """Summary of all automated analyses."""
    doc_id: str
    filename: str
    analysis_timestamp: str
    
    # Analysis Results
    timeline_events_count: int = 0
    calendar_events_count: int = 0
    complaints_identified: int = 0
    rights_count: int = 0
    missteps_count: int = 0
    tactics_recommended: int = 0
    
    # Content Summaries
    timeline_summary: str = ""
    calendar_summary: str = ""
    complaints_summary: str = ""
    rights_summary: str = ""
    missteps_summary: str = ""
    tactics_summary: str = ""
    
    # Progress & Status
    overall_progress: int = 0  # 0-100
    analysis_confidence: float = 0.0  # 0.0-1.0
    
    # Actionable Items
    recommended_actions: List[Dict[str, Any]] = field(default_factory=list)
    urgent_actions: List[Dict[str, Any]] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'doc_id': self.doc_id,
            'filename': self.filename,
            'analysis_timestamp': self.analysis_timestamp,
            'timeline_events': self.timeline_events_count,
            'calendar_events': self.calendar_events_count,
            'complaints': self.complaints_identified,
            'rights': self.rights_count,
            'missteps': self.missteps_count,
            'tactics': self.tactics_recommended,
            'summaries': {
                'timeline': self.timeline_summary,
                'calendar': self.calendar_summary,
                'complaints': self.complaints_summary,
                'rights': self.rights_summary,
                'missteps': self.missteps_summary,
                'tactics': self.tactics_summary,
            },
            'progress': self.overall_progress,
            'confidence': self.analysis_confidence,
            'recommended_actions': self.recommended_actions,
            'urgent_actions': self.urgent_actions,
            'next_steps': self.next_steps,
        }


class AutoModeSummaryService:
    """
    Generates comprehensive summaries and actionable recommendations from analysis results.
    """

    async def generate_summary(
        self,
        doc_id: str,
        filename: str,
        analysis_results: Dict[str, Any]
    ) -> AnalysisSummary:
        """
        Generate comprehensive summary from analysis results.
        """
        summary = AnalysisSummary(
            doc_id=doc_id,
            filename=filename,
            analysis_timestamp=datetime.now().isoformat()
        )

        try:
            # Timeline Analysis
            timeline_events = analysis_results.get('timeline_events', [])
            summary.timeline_events_count = len(timeline_events)
            summary.timeline_summary = self._summarize_timeline(timeline_events)

            # Calendar Analysis
            calendar_events = analysis_results.get('calendar_events', [])
            summary.calendar_events_count = len(calendar_events)
            summary.calendar_summary = self._summarize_calendar(calendar_events)

            # Complaints Analysis
            complaints = analysis_results.get('complaints', [])
            summary.complaints_identified = len(complaints)
            summary.complaints_summary = self._summarize_complaints(complaints)

            # Rights Assessment
            rights = analysis_results.get('rights_assessment', {})
            summary.rights_count = len(rights.get('strengths', []))
            summary.rights_summary = self._summarize_rights(rights)

            # Legal Missteps
            missteps = analysis_results.get('legal_missteps', [])
            summary.missteps_count = len(missteps)
            summary.missteps_summary = self._summarize_missteps(missteps)

            # Tactics
            tactics = analysis_results.get('proactive_tactics', [])
            summary.tactics_recommended = len(tactics)
            summary.tactics_summary = self._summarize_tactics(tactics)

            # Generate Recommended Actions
            summary.recommended_actions = await self._generate_recommended_actions(
                analysis_results, summary
            )

            # Generate Urgent Actions
            summary.urgent_actions = self._generate_urgent_actions(
                analysis_results, summary
            )

            # Generate Next Steps
            summary.next_steps = self._generate_next_steps(
                analysis_results, summary
            )

            # Calculate Progress
            summary.overall_progress = self._calculate_progress(summary)
            summary.analysis_confidence = self._calculate_confidence(analysis_results)

            logger.info(f"Generated summary for doc {doc_id}: {summary.timeline_events_count} timeline events, "
                       f"{summary.complaints_identified} complaints, {summary.tactics_recommended} tactics")

        except Exception as e:
            logger.error(f"Error generating summary for {doc_id}: {e}")

        return summary

    def _summarize_timeline(self, timeline_events: List[Dict[str, Any]]) -> str:
        """Generate timeline summary."""
        if not timeline_events:
            return "No timeline events extracted from document."

        # Group by event type
        by_type = {}
        for event in timeline_events:
            event_type = event.get('event_type', 'other')
            if event_type not in by_type:
                by_type[event_type] = []
            by_type[event_type].append(event)

        # Build summary
        parts = [f"Extracted {len(timeline_events)} timeline events:"]
        for event_type, events in by_type.items():
            parts.append(f"  • {event_type}: {len(events)} event(s)")

        # Find earliest and latest dates
        dates = [e.get('event_date') for e in timeline_events if e.get('event_date')]
        if dates:
            parts.append(f"  • Timeline span: {min(dates)} to {max(dates)}")

        # Identify deadlines
        deadlines = [e for e in timeline_events if e.get('is_deadline')]
        if deadlines:
            parts.append(f"  • Critical deadlines: {len(deadlines)} identified")

        return "\n".join(parts)

    def _summarize_calendar(self, calendar_events: List[Dict[str, Any]]) -> str:
        """Generate calendar summary."""
        if not calendar_events:
            return "No calendar events generated."

        # Group by type
        by_type = {}
        for event in calendar_events:
            event_type = event.get('event_type', 'other')
            if event_type not in by_type:
                by_type[event_type] = 0
            by_type[event_type] += 1

        parts = [f"Generated {len(calendar_events)} calendar events:"]
        for event_type, count in by_type.items():
            parts.append(f"  • {event_type}: {count} event(s)")

        # Find upcoming events
        upcoming = [e for e in calendar_events if not e.get('end_date', e.get('start_date', ''))]
        if upcoming:
            parts.append(f"  • Upcoming events with reminders: {len(upcoming)}")

        return "\n".join(parts)

    def _summarize_complaints(self, complaints: List[Dict[str, Any]]) -> str:
        """Generate complaints summary."""
        if not complaints:
            return "No complaints to file identified."

        parts = [f"Identified {len(complaints)} potential complaints to file:"]
        agency_types = {}
        for complaint in complaints:
            agency_type = complaint.get('type', 'unknown')
            if agency_type not in agency_types:
                agency_types[agency_type] = 0
            agency_types[agency_type] += 1

        for agency_type, count in agency_types.items():
            parts.append(f"  • {agency_type}: {count} complaint(s)")

        return "\n".join(parts)

    def _summarize_rights(self, rights: Dict[str, Any]) -> str:
        """Generate rights assessment summary."""
        strengths = rights.get('strengths', [])
        weaknesses = rights.get('weaknesses', [])

        parts = []
        if strengths:
            parts.append(f"Your Strengths ({len(strengths)}):")
            for strength in strengths[:3]:  # Top 3
                parts.append(f"  • {strength}")
            if len(strengths) > 3:
                parts.append(f"  ... and {len(strengths) - 3} more")

        if weaknesses:
            parts.append(f"\nAreas to Address ({len(weaknesses)}):")
            for weakness in weaknesses[:3]:  # Top 3
                parts.append(f"  • {weakness}")
            if len(weaknesses) > 3:
                parts.append(f"  ... and {len(weaknesses) - 3} more")

        return "\n".join(parts) if parts else "Rights assessment generated."

    def _summarize_missteps(self, missteps: List[str]) -> str:
        """Generate legal missteps summary."""
        if not missteps:
            return "No legal procedural violations detected."

        parts = [f"Detected {len(missteps)} potential legal missteps:"]
        for i, misstep in enumerate(missteps[:5], 1):  # Top 5
            parts.append(f"  {i}. {misstep}")
        if len(missteps) > 5:
            parts.append(f"  ... and {len(missteps) - 5} more")

        return "\n".join(parts)

    def _summarize_tactics(self, tactics: List[Dict[str, Any]]) -> str:
        """Generate tactics summary."""
        if not tactics:
            return "No proactive defense tactics recommended at this time."

        parts = [f"Recommended {len(tactics)} proactive defense tactics:"]
        for i, tactic in enumerate(tactics[:4], 1):  # Top 4
            tactic_type = tactic.get('tactic_type', 'unknown')
            parts.append(f"  {i}. {tactic_type}: {tactic.get('reasoning', 'See details for more information')}")
        if len(tactics) > 4:
            parts.append(f"  ... and {len(tactics) - 4} more")

        return "\n".join(parts)

    async def _generate_recommended_actions(
        self,
        analysis_results: Dict[str, Any],
        summary: AnalysisSummary
    ) -> List[Dict[str, Any]]:
        """Generate list of recommended actions."""
        actions = []

        # Action 1: Review timeline
        if summary.timeline_events_count > 0:
            actions.append({
                'action_id': 'review_timeline',
                'title': 'Review Extracted Timeline',
                'description': f'{summary.timeline_events_count} events were extracted. Review to ensure accuracy.',
                'priority': 'high' if summary.timeline_events_count > 5 else 'medium',
                'estimated_time': '5-10 minutes',
                'link': f'/timeline?doc_id={summary.doc_id}'
            })

        # Action 2: File complaints
        if summary.complaints_identified > 0:
            actions.append({
                'action_id': 'file_complaints',
                'title': f'File {summary.complaints_identified} Complaint(s)',
                'description': 'Regulatory agencies identified where you can file complaints.',
                'priority': 'high',
                'estimated_time': '20-30 minutes per complaint',
                'link': f'/complaints?doc_id={summary.doc_id}'
            })

        # Action 3: Review legal rights
        if summary.rights_count > 0:
            actions.append({
                'action_id': 'review_rights',
                'title': 'Review Your Legal Rights',
                'description': 'Based on document analysis, review your rights and protections.',
                'priority': 'high',
                'estimated_time': '10-15 minutes',
                'link': f'/legal-analysis?doc_id={summary.doc_id}'
            })

        # Action 4: Implement tactics
        if summary.tactics_recommended > 0:
            actions.append({
                'action_id': 'implement_tactics',
                'title': f'Consider {summary.tactics_recommended} Defense Tactic(s)',
                'description': 'Proactive strategies to strengthen your position.',
                'priority': 'medium',
                'estimated_time': '15-20 minutes',
                'link': f'/tactics?doc_id={summary.doc_id}'
            })

        # Action 5: Address missteps
        if summary.missteps_count > 0:
            actions.append({
                'action_id': 'address_missteps',
                'title': f'Address {summary.missteps_count} Legal Misstep(s)',
                'description': 'Procedural violations that could impact your case.',
                'priority': 'critical',
                'estimated_time': '15-30 minutes',
                'link': f'/legal-missteps?doc_id={summary.doc_id}'
            })

        return actions

    def _generate_urgent_actions(
        self,
        analysis_results: Dict[str, Any],
        summary: AnalysisSummary
    ) -> List[Dict[str, Any]]:
        """Generate list of urgent actions that need immediate attention."""
        urgent = []

        # Urgent: Legal missteps
        if summary.missteps_count > 0:
            urgent.append({
                'action': 'address_missteps',
                'message': f'⚠️ {summary.missteps_count} legal procedural violation(s) detected',
                'severity': 'critical',
                'deadline': 'Immediate'
            })

        # Urgent: Critical deadlines
        timeline_events = analysis_results.get('timeline_events', [])
        deadlines = [e for e in timeline_events if e.get('is_deadline')]
        urgent_deadlines = [d for d in deadlines if d.get('urgency') == 'critical']
        if urgent_deadlines:
            urgent.append({
                'action': 'review_deadlines',
                'message': f'⏰ {len(urgent_deadlines)} critical deadline(s)',
                'severity': 'critical',
                'deadline': 'Within 24 hours'
            })

        # Urgent: File complaints
        if summary.complaints_identified > 0:
            urgent.append({
                'action': 'file_complaints',
                'message': f'📋 {summary.complaints_identified} complaint(s) ready to file',
                'severity': 'high',
                'deadline': 'Within 3 days'
            })

        return urgent

    def _generate_next_steps(
        self,
        analysis_results: Dict[str, Any],
        summary: AnalysisSummary
    ) -> List[str]:
        """Generate list of next steps."""
        steps = []

        steps.append("1. Review the automatically extracted timeline and calendar for accuracy")
        
        if summary.missteps_count > 0:
            steps.append("2. ⚠️ ADDRESS MISSTEPS IMMEDIATELY - Review legal procedural violations")
        else:
            steps.append("2. Review your legal rights and protections identified in the analysis")

        if summary.complaints_identified > 0:
            steps.append("3. Consider filing complaints with identified regulatory agencies")
        
        if summary.tactics_recommended > 0:
            steps.append("4. Evaluate and plan implementation of recommended defense tactics")

        steps.append("5. Gather any additional supporting documentation")
        steps.append("6. Upload more documents to build a stronger case")
        steps.append("7. Share analysis with legal counsel or advocate if available")

        return steps

    def _calculate_progress(self, summary: AnalysisSummary) -> int:
        """Calculate overall progress percentage (0-100)."""
        completion_factors = [
            (1 if summary.timeline_events_count > 0 else 0, 15),  # Timeline: 15%
            (1 if summary.calendar_events_count > 0 else 0, 10),  # Calendar: 10%
            (1 if summary.complaints_identified > 0 else 0, 15),  # Complaints: 15%
            (1 if summary.rights_count > 0 else 0, 15),           # Rights: 15%
            (1 if summary.missteps_count >= 0 else 0, 15),        # Missteps check: 15%
            (1 if summary.tactics_recommended > 0 else 0, 15),    # Tactics: 15%
            (1, 5),                                                # Document processed: 5%
        ]

        total = sum(factor * weight for factor, weight in completion_factors)
        return min(100, total)

    def _calculate_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on analysis quality (0.0-1.0).
        """
        confidence = 0.5  # Start at baseline

        # Add confidence based on number of events found
        timeline_count = len(analysis_results.get('timeline_events', []))
        confidence += min(0.2, timeline_count * 0.05)  # Max +0.2 for timeline

        # Add confidence based on legal missteps found
        missteps = analysis_results.get('legal_missteps', [])
        if missteps:
            confidence += 0.15

        # Add confidence based on multiple analysis types
        analysis_types = sum([
            1 if analysis_results.get('timeline_events') else 0,
            1 if analysis_results.get('calendar_events') else 0,
            1 if analysis_results.get('complaints') else 0,
            1 if analysis_results.get('rights_assessment') else 0,
            1 if analysis_results.get('proactive_tactics') else 0,
        ])
        confidence += (analysis_types / 5) * 0.15  # Up to +0.15 for multiple analyses

        return min(1.0, confidence)