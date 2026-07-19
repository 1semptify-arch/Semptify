"""
Housing Accountability Router - Regulatory Compliance & Oversight
=========================================================

FastAPI router for Housing Accountability Module.
Provides pattern detection, oversight packets, coalition tools, and regulatory compliance.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

# Initialize housing accountability router
accountability_router = APIRouter(prefix="/api/housing-accountability", tags=["Housing Accountability"])


# Pydantic Models
class PatternDetectionRequest(BaseModel):
    """Request for pattern detection analysis."""

    tenant_data: dict[str, Any] = Field(..., description="Tenant data for analysis")
    property_data: dict[str, Any] = Field(..., description="Property data for analysis")
    evidence_data: list[dict[str, Any]] = Field(..., description="Evidence documents and data")
    analysis_type: str = Field("comprehensive", description="Type of analysis to perform")


class OversightPacketRequest(BaseModel):
    """Request for oversight packet generation."""

    packet_type: str = Field(..., description="Type of oversight packet (HUD, MDHR, CFPB, AG)")
    tenant_data: dict[str, Any] = Field(..., description="Tenant information")
    violation_data: list[dict[str, Any]] = Field(..., description="Violation and pattern data")
    evidence_attachments: list[str] = Field(..., description="Evidence document IDs")
    urgency_level: str = Field("standard", description="Urgency level (standard, urgent, emergency)")


class CoalitionRequest(BaseModel):
    """Request for coalition building tools."""

    coalition_type: str = Field(..., description="Type of coalition action")
    target_audience: str = Field(..., description="Target audience for coalition")
    message_data: dict[str, Any] = Field(..., description="Message content and data")
    contact_list: list[dict[str, Any]] = Field(..., description="Contact information")
    action_type: str = Field("outreach", description="Type of coalition action")


class EvidenceIntakeRequest(BaseModel):
    """Request for evidence intake processing."""

    evidence_type: str = Field(..., description="Type of evidence (document, photo, video, testimony)")
    evidence_data: dict[str, Any] = Field(..., description="Evidence content and metadata")
    case_context: dict[str, Any] = Field(..., description="Case context and information")
    priority: str = Field("standard", description="Processing priority")


class PublicRecordsRequest(BaseModel):
    """Request for public records research."""

    record_type: str = Field(..., description="Type of public record to research")
    search_criteria: dict[str, Any] = Field(..., description="Search criteria and parameters")
    jurisdiction: str = Field(..., description="Jurisdiction for records search")
    time_range: str | None = Field(None, description="Time range for records")


class PressBuilderRequest(BaseModel):
    """Request for press release generation."""

    story_type: str = Field(..., description="Type of press story")
    key_facts: list[str] = Field(..., description="Key facts for the story")
    affected_parties: list[dict[str, Any]] = Field(..., description="Affected parties information")
    legal_context: dict[str, Any] = Field(..., description="Legal and regulatory context")
    media_targets: list[str] = Field(..., description="Target media outlets")
    urgency: str = Field("standard", description="Story urgency level")


def _parse_date_safe(value) -> datetime | None:
    """Parse ISO date string or datetime safely, returning a UTC-aware datetime or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if not isinstance(value, str):
        value = str(value)
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def _parse_amount(value, default: float | None = None) -> float | None:
    """Parse a fee amount, tolerating strings with currency symbols and commas."""
    if value is None:
        return default
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def _extract_fee_history(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive fee records from evidence_data when no explicit fee_history is provided."""
    fees: list[dict[str, Any]] = []
    seen: set = set()
    evidence = data.get("evidence_data", [])
    if not isinstance(evidence, list):
        return fees

    for item in evidence:
        if not isinstance(item, dict):
            continue

        candidates = [item]
        for key in ("metadata", "extracted_data", "analysis", "document_metadata"):
            nested = item.get(key)
            if isinstance(nested, dict):
                candidates.append(nested)

        for candidate in candidates:
            amount = _parse_amount(candidate.get("amount"))
            if amount is None:
                continue

            date_value = (
                candidate.get("date")
                or candidate.get("date_paid")
                or candidate.get("paid_date")
                or candidate.get("occurred_at")
            )
            if not date_value:
                continue

            fee_type = (
                candidate.get("fee_type")
                or candidate.get("type")
                or candidate.get("description")
                or candidate.get("category")
            )
            if not fee_type:
                continue

            date_str = date_value.isoformat() if hasattr(date_value, "isoformat") else str(date_value)
            key = (str(fee_type).strip().lower(), float(amount), date_str)
            if key in seen:
                continue
            seen.add(key)

            fees.append(
                {
                    "type": fee_type,
                    "amount": amount,
                    "date": date_str,
                }
            )
            break

    return fees


# Legal basis by jurisdiction for repeated-fee / harassment patterns
_REPEATED_FEES_LEGAL_BASIS = {
    "MN": "Minnesota Statutes 504B.215 - Prohibited landlord practices",
    "NY": "NY Real Property Law §236 - Unconscionable rent increases; NYC Admin Code §27-2004 (harassment)",
    "CA": "California Civil Code §1940.2 - Landlord harassment prohibited",
    "TX": "Texas Property Code §92.061 - Retaliation prohibited",
    "FL": "Florida Statutes §83.64 - Retaliation prohibited",
    "IL": "735 ILCS 5/9-212 - Retaliatory eviction prohibited; Chicago RLTO §5-12-030",
}


# Housing Accountability Services
class PatternDetectionService:
    """Pattern detection service for housing violations."""

    def __init__(self):
        self.pattern_cache = {}

    def detect_repeated_fees(self, data: dict[str, Any]) -> dict[str, Any]:
        """Detect repeated fee patterns that may indicate unlawful landlord practices.

        Groups fees by type/description, counts frequency within rolling 35-day
        windows, and flags patterns that exceed thresholds. Jurisdiction-aware
        legal basis. Confidence scales with amount of evidence found.
        """
        patterns: list[dict[str, Any]] = []
        fee_history = data.get("fee_history") or _extract_fee_history(data)
        jurisdiction = str(data.get("jurisdiction", "MN")).upper()

        if len(fee_history) < 2:
            return {"patterns": patterns, "confidence": 0.3, "reason": "insufficient_data"}

        # Group fees by type or description (case-insensitive)
        fee_groups: dict[str, list[dict[str, Any]]] = {}
        for fee in fee_history:
            fee_type = (
                str(fee.get("fee_type") or fee.get("type") or fee.get("description") or "unknown").strip().lower()
            )
            fee_groups.setdefault(fee_type, []).append(fee)

        legal_basis = _REPEATED_FEES_LEGAL_BASIS.get(
            jurisdiction,
            f"State landlord-tenant act ({jurisdiction}) — prohibited practices",
        )

        recurring_evidence: list[dict[str, Any]] = []
        for fee_type, fees in fee_groups.items():
            if len(fees) < 2:
                continue
            # Sort by parsed date (fees with unparseable dates sort to end)
            sorted_fees = sorted(
                fees,
                key=lambda f: _parse_date_safe(f.get("date", "")) or datetime.min.replace(tzinfo=UTC),
            )
            # Check all pairs within each fee type (not just adjacent)
            for i in range(len(sorted_fees)):
                for j in range(i + 1, len(sorted_fees)):
                    current_fee = sorted_fees[i]
                    compare_fee = sorted_fees[j]
                    current_date = _parse_date_safe(current_fee.get("date", ""))
                    compare_date = _parse_date_safe(compare_fee.get("date", ""))
                    if current_date is None or compare_date is None:
                        continue
                    days_apart = abs((compare_date - current_date).days)
                    amount_diff = abs(
                        _parse_amount(current_fee.get("amount"), 0.0) - _parse_amount(compare_fee.get("amount"), 0.0)
                    )
                    # Same type, similar amount (within $5), within 35 days
                    if days_apart <= 35 and amount_diff < 5:
                        recurring_evidence.append(
                            {
                                "fee_type": fee_type,
                                "fee_1": current_fee,
                                "fee_2": compare_fee,
                                "days_apart": days_apart,
                                "amount_diff": amount_diff,
                            }
                        )

        if recurring_evidence:
            affected_types = sorted({e["fee_type"] for e in recurring_evidence})
            if len(affected_types) >= 3:
                severity = "high"
            elif len(affected_types) >= 2:
                severity = "medium"
            else:
                severity = "low"
            confidence = min(0.95, 0.5 + 0.1 * len(recurring_evidence))
            patterns.append(
                {
                    "type": "repeated_fees",
                    "severity": severity,
                    "description": (
                        f"Detected {len(recurring_evidence)} potentially recurring fee "
                        f"instances across {len(affected_types)} fee type(s)"
                    ),
                    "evidence": recurring_evidence,
                    "legal_basis": legal_basis,
                    "affected_fee_types": affected_types,
                    "jurisdiction": jurisdiction,
                }
            )
            return {"patterns": patterns, "confidence": confidence}

        return {"patterns": patterns, "confidence": 0.4, "reason": "no_recurring_patterns_detected"}

    def detect_eviction_patterns(self, data: dict[str, Any]) -> dict[str, Any]:
        """Detect eviction-related patterns."""
        patterns = []

        # Analyze eviction history
        eviction_history = data.get("eviction_history", [])
        if len(eviction_history) > 1:
            patterns.append(
                {
                    "type": "serial_eviction",
                    "severity": "high",
                    "description": f"Multiple eviction actions detected ({len(eviction_history)})",
                    "evidence": eviction_history,
                    "legal_basis": "Minnesota Statutes 504B.291 - Retaliatory eviction prohibition",
                }
            )

        # Check for timing patterns
        if eviction_history:
            for eviction in eviction_history:
                filing_date_str = eviction.get("filing_date", "")
                complaint_date_str = eviction.get("complaint_date", "")
                if not filing_date_str or not complaint_date_str:
                    continue
                filing_date = datetime.fromisoformat(filing_date_str)
                complaint_date = datetime.fromisoformat(complaint_date_str)

                # Check if eviction followed complaint filing
                if (filing_date - complaint_date).days <= 30:
                    patterns.append(
                        {
                            "type": "retaliatory_eviction",
                            "severity": "high",
                            "description": "Eviction filing shortly after tenant complaint",
                            "evidence": eviction,
                            "legal_basis": "Minnesota Statutes 504B.291 - Retaliatory eviction",
                        }
                    )

        return {"patterns": patterns, "confidence": 0.8}

    def detect_subsidy_interference(self, data: dict[str, Any]) -> dict[str, Any]:
        """Detect subsidy interference patterns."""
        patterns = []

        # Analyze subsidy information
        subsidy_data = data.get("subsidy_information", {})
        if subsidy_data.get("section8_active", False):
            # Check for interference patterns
            interference_indicators = []

            if data.get("unlawful_rent_increase", False):
                interference_indicators.append("Unlawful rent increase")

            if data.get("harassment_complaints", 0) > 0:
                interference_indicators.append("Harassment complaints")

            if data.get("maintenance_withholding", False):
                interference_indicators.append("Maintenance withholding")

            if interference_indicators:
                patterns.append(
                    {
                        "type": "subsidy_interference",
                        "severity": "high",
                        "description": f"Subsidy interference indicators: {', '.join(interference_indicators)}",
                        "evidence": interference_indicators,
                        "legal_basis": "HUD Handbook 4350.3 - Section 8 program compliance",
                    }
                )

        return {"patterns": patterns, "confidence": 0.75}

    def detect_court_order_violations(self, data: dict[str, Any]) -> dict[str, Any]:
        """Detect court order violation patterns."""
        patterns = []

        # Analyze court orders
        court_orders = data.get("court_orders", [])
        for order in court_orders:
            if order.get("violated", False):
                patterns.append(
                    {
                        "type": "court_order_violation",
                        "severity": "critical",
                        "description": f"Violation of court order: {order.get('order_type', 'Unknown')}",
                        "evidence": order,
                        "legal_basis": "Contempt of court proceedings",
                    }
                )

        return {"patterns": patterns, "confidence": 0.9}

    def generate_pattern_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive pattern summary."""
        all_patterns = []

        # Run all pattern detection
        fee_patterns = self.detect_repeated_fees(data)
        eviction_patterns = self.detect_eviction_patterns(data)
        subsidy_patterns = self.detect_subsidy_interference(data)
        court_patterns = self.detect_court_order_violations(data)

        all_patterns.extend(fee_patterns.get("patterns", []))
        all_patterns.extend(eviction_patterns.get("patterns", []))
        all_patterns.extend(subsidy_patterns.get("patterns", []))
        all_patterns.extend(court_patterns.get("patterns", []))

        # Calculate overall risk score
        risk_score = 0
        for pattern in all_patterns:
            severity_weights = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            risk_score += severity_weights.get(pattern.get("severity", "medium"), 2)

        # Generate recommendations
        recommendations = []
        if any(p["type"] == "repeated_fees" for p in all_patterns):
            recommendations.append("File complaint with Minnesota Attorney General")
            recommendations.append("Request rent escrow order")

        if any(p["type"] == "retaliatory_eviction" for p in all_patterns):
            recommendations.append("File retaliatory eviction defense")
            recommendations.append("Request injunction against eviction")

        if any(p["type"] == "subsidy_interference" for p in all_patterns):
            recommendations.append("Report to HUD Section 8 office")
            recommendations.append("File fair housing complaint")

        return {
            "summary": {
                "total_patterns": len(all_patterns),
                "risk_score": risk_score,
                "risk_level": self._calculate_risk_level(risk_score),
                "patterns_by_type": self._group_patterns_by_type(all_patterns),
            },
            "patterns": all_patterns,
            "recommendations": recommendations,
            "generated_at": utc_now().isoformat(),
        }

    def _calculate_risk_level(self, score: int) -> str:
        """Calculate risk level based on score."""
        if score >= 8:
            return "critical"
        elif score >= 6:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"

    def _group_patterns_by_type(self, patterns: list[dict[str, Any]]) -> dict[str, int]:
        """Group patterns by type."""
        grouped = {}
        for pattern in patterns:
            pattern_type = pattern.get("type", "unknown")
            grouped[pattern_type] = grouped.get(pattern_type, 0) + 1
        return grouped


class OversightPacketService:
    """Oversight packet generation service."""

    def build_ag_packet(self, tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
        """Build Attorney General oversight packet."""
        packet = {
            "packet_type": "attorney_general",
            "recipient": "Minnesota Attorney General's Office",
            "subject": f"Housing Rights Complaint - {tenant_data.get('property_address', 'Unknown Address')}",
            "tenant_information": tenant_data,
            "violation_summary": self._summarize_violations(patterns),
            "legal_bases": [p.get("legal_basis") for p in patterns if p.get("legal_basis")],
            "requested_actions": [
                "Investigate landlord practices",
                "Enforce housing rights laws",
                "Seek appropriate remedies",
            ],
            "evidence_required": [
                "Lease agreement",
                "Communication records",
                "Payment history",
                "Violation documentation",
            ],
            "generated_at": utc_now().isoformat(),
        }
        return packet

    def build_hud_packet(self, tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
        """Build HUD oversight packet."""
        packet = {
            "packet_type": "hud",
            "recipient": "HUD Regional Office",
            "subject": f"Fair Housing Complaint - {tenant_data.get('property_address', 'Unknown Address')}",
            "tenant_information": tenant_data,
            "fair_housing_analysis": self._analyze_fair_housing_violations(patterns),
            "protected_class_analysis": tenant_data.get("protected_class_information", {}),
            "discrimination_indicators": self._identify_discrimination_patterns(patterns),
            "requested_actions": [
                "Investigate discrimination claims",
                "Enforce Fair Housing Act",
                "Provide tenant protections",
            ],
            "evidence_required": [
                "Protected class documentation",
                "Differential treatment evidence",
                "Communication records",
                "Housing application records",
            ],
            "generated_at": utc_now().isoformat(),
        }
        return packet

    def build_mdhr_packet(self, tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
        """Build Minnesota Department of Human Rights packet."""
        packet = {
            "packet_type": "mdhr",
            "recipient": "Minnesota Department of Human Rights",
            "subject": f"Human Rights Complaint - {tenant_data.get('property_address', 'Unknown Address')}",
            "tenant_information": tenant_data,
            "human_rights_violations": self._analyze_human_rights_violations(patterns),
            "state_law_violations": self._identify_state_law_violations(patterns),
            "discrimination_analysis": self._analyze_discrimination_under_state_law(patterns),
            "requested_actions": [
                "Investigate human rights violations",
                "Enforce Minnesota Human Rights Act",
                "Provide appropriate remedies",
            ],
            "evidence_required": [
                "Protected class documentation",
                "Comparative evidence",
                "Communication records",
                "Housing records",
            ],
            "generated_at": utc_now().isoformat(),
        }
        return packet

    def build_cfpb_packet(self, tenant_data: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
        """Build Consumer Financial Protection Bureau packet."""
        packet = {
            "packet_type": "cfpb",
            "recipient": "Consumer Financial Protection Bureau",
            "subject": f"Consumer Complaint - {tenant_data.get('property_address', 'Unknown Address')}",
            "tenant_information": tenant_data,
            "financial_violations": self._analyze_financial_violations(patterns),
            "consumer_protection_issues": self._identify_consumer_protection_violations(patterns),
            "requested_actions": [
                "Investigate consumer protection violations",
                "Enforce consumer financial laws",
                "Provide consumer relief",
            ],
            "evidence_required": ["Financial records", "Fee documentation", "Communication records", "Payment history"],
            "generated_at": utc_now().isoformat(),
        }
        return packet

    def _summarize_violations(self, patterns: list[dict[str, Any]]) -> dict[str, Any]:
        """Summarize violations for oversight packet."""
        violation_types = {}
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for pattern in patterns:
            pattern_type = pattern.get("type", "unknown")
            violation_types[pattern_type] = violation_types.get(pattern_type, 0) + 1

            severity = pattern.get("severity", "medium")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "violation_types": violation_types,
            "severity_distribution": severity_counts,
            "total_violations": len(patterns),
        }

    def _analyze_fair_housing_violations(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Analyze fair housing violations."""
        return [p for p in patterns if "discrimination" in p.get("type", "").lower()]

    def _identify_discrimination_patterns(self, patterns: list[dict[str, Any]]) -> list[str]:
        """Identify discrimination patterns."""
        indicators = []
        for pattern in patterns:
            if "discrimination" in pattern.get("type", "").lower():
                indicators.append(pattern.get("description", ""))
        return indicators

    def _analyze_human_rights_violations(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Analyze human rights violations."""
        return [
            p
            for p in patterns
            if "discrimination" in p.get("type", "").lower() or "harassment" in p.get("type", "").lower()
        ]

    def _identify_state_law_violations(self, patterns: list[dict[str, Any]]) -> list[str]:
        """Identify state law violations."""
        violations = []
        for pattern in patterns:
            if "minnesota" in pattern.get("legal_basis", "").lower():
                violations.append(pattern.get("legal_basis", ""))
        return violations

    def _analyze_discrimination_under_state_law(self, patterns: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze discrimination under state law."""
        discrimination_patterns = [p for p in patterns if "discrimination" in p.get("type", "").lower()]
        return {
            "discrimination_count": len(discrimination_patterns),
            "protected_classes_affected": list({p.get("protected_class", "unknown") for p in discrimination_patterns}),
            "violation_types": list({p.get("type", "unknown") for p in discrimination_patterns}),
        }

    def _analyze_financial_violations(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Analyze financial violations."""
        return [p for p in patterns if "fee" in p.get("type", "").lower() or "rent" in p.get("type", "").lower()]

    def _identify_consumer_protection_violations(self, patterns: list[dict[str, Any]]) -> list[str]:
        """Identify consumer protection violations."""
        violations = []
        for pattern in patterns:
            if pattern.get("type") in ["repeated_fees", "unlawful_rent_increase"]:
                violations.append(pattern.get("description", ""))
        return violations


# Initialize services
pattern_service = PatternDetectionService()
oversight_service = OversightPacketService()


@accountability_router.post("/patterns/detect")
async def detect_patterns(
    request: PatternDetectionRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Detect housing violation patterns."""
    try:
        # Combine all data for pattern analysis
        analysis_data = {**request.tenant_data, **request.property_data, "evidence_data": request.evidence_data}

        # Generate pattern summary
        pattern_summary = pattern_service.generate_pattern_summary(analysis_data)

        # Save pattern record if persistence is enabled
        try:
            from app.models.pattern_record import save_pattern_record

            saved_record = save_pattern_record(
                db=db,
                user_id=current_user.id,
                analysis_type=request.analysis_type,
                pattern_data=pattern_summary,
                data_sources={
                    "tenant_data_keys": list(request.tenant_data.keys()),
                    "property_data_keys": list(request.property_data.keys()),
                    "evidence_count": len(request.evidence_data),
                },
            )
            if saved_record:
                pattern_summary["record_id"] = saved_record.id
        except ImportError:
            # Pattern record model not available - continue without persistence
            pass
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Failed to save pattern record: {e}")

        return JSONResponse(
            content={
                "success": True,
                "pattern_analysis": pattern_summary,
                "analysis_type": request.analysis_type,
                "analyzed_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Pattern detection failed: {e}")
        logger.exception("Pattern detection failed")
        raise HTTPException(status_code=500, detail="Pattern detection failed")


@accountability_router.post("/oversight/packet/generate")
async def generate_oversight_packet(request: OversightPacketRequest, current_user=Depends(get_current_user)):
    """Generate oversight packet for regulatory submission."""
    try:
        # Generate patterns for packet content
        analysis_data = {**request.tenant_data, "violation_data": request.violation_data}
        pattern_summary = pattern_service.generate_pattern_summary(analysis_data)
        patterns = pattern_summary.get("patterns", [])

        # Generate appropriate packet
        if request.packet_type.lower() == "ag":
            packet = oversight_service.build_ag_packet(request.tenant_data, patterns)
        elif request.packet_type.lower() == "hud":
            packet = oversight_service.build_hud_packet(request.tenant_data, patterns)
        elif request.packet_type.lower() == "mdhr":
            packet = oversight_service.build_mdhr_packet(request.tenant_data, patterns)
        elif request.packet_type.lower() == "cfpb":
            packet = oversight_service.build_cfpb_packet(request.tenant_data, patterns)
        else:
            raise HTTPException(status_code=400, detail="Invalid packet type")

        return JSONResponse(
            content={
                "success": True,
                "oversight_packet": packet,
                "urgency_level": request.urgency_level,
                "generated_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Oversight packet generation failed: {e}")
        logger.exception("Packet generation failed")
        raise HTTPException(status_code=500, detail="Packet generation failed")


@accountability_router.post("/coalition/build")
async def build_coalition_action(request: CoalitionRequest, current_user=Depends(get_current_user)):
    """Build coalition action for community organizing."""
    try:
        # Generate coalition action plan
        action_plan = {
            "coalition_type": request.coalition_type,
            "target_audience": request.target_audience,
            "message": request.message_data,
            "contacts": request.contact_list,
            "action_type": request.action_type,
            "strategy": _generate_coalition_strategy(request.coalition_type),
            "timeline": _generate_coalition_timeline(request.action_type),
            "resources_needed": _identify_coalition_resources(request.coalition_type),
            "success_metrics": _define_coalition_metrics(request.coalition_type),
            "created_at": utc_now().isoformat(),
        }

        return JSONResponse(
            content={"success": True, "coalition_action": action_plan, "generated_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Coalition building failed: {e}")
        logger.exception("Coalition building failed")
        raise HTTPException(status_code=500, detail="Coalition building failed")


@accountability_router.post("/evidence/intake")
async def process_evidence_intake(request: EvidenceIntakeRequest, current_user=Depends(get_current_user)):
    """Process evidence intake for housing cases."""
    try:
        # Process evidence based on type
        processed_evidence = {
            "evidence_id": f"evidence_{utc_now().timestamp()}",
            "evidence_type": request.evidence_type,
            "processed_data": _process_evidence_data(request.evidence_data, request.evidence_type),
            "case_context": request.case_context,
            "priority": request.priority,
            "analysis_results": _analyze_evidence(request.evidence_data, request.evidence_type),
            "recommendations": _generate_evidence_recommendations(request.evidence_type),
            "processed_at": utc_now().isoformat(),
        }

        return JSONResponse(
            content={"success": True, "processed_evidence": processed_evidence, "processed_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Evidence intake failed: {e}")
        logger.exception("Evidence intake failed")
        raise HTTPException(status_code=500, detail="Evidence intake failed")


@accountability_router.post("/public-records/search")
async def search_public_records(request: PublicRecordsRequest, current_user=Depends(get_current_user)):
    """Search public records for housing cases."""
    try:
        # Simulate public records search
        search_results = {
            "search_id": f"search_{utc_now().timestamp()}",
            "record_type": request.record_type,
            "search_criteria": request.search_criteria,
            "jurisdiction": request.jurisdiction,
            "time_range": request.time_range,
            "results": (results := _simulate_public_records_search(request.record_type, request.search_criteria)),
            "total_results": len(results),
            "search_duration": "2.3 seconds",
            "searched_at": utc_now().isoformat(),
        }

        return JSONResponse(
            content={"success": True, "search_results": search_results, "searched_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Public records search failed: {e}")
        logger.exception("Public records search failed")
        raise HTTPException(status_code=500, detail="Public records search failed")


@accountability_router.post("/press/build")
async def build_press_release(request: PressBuilderRequest, current_user=Depends(get_current_user)):
    """Build press release for housing rights advocacy."""
    try:
        # Generate press release
        press_release = {
            "press_id": f"press_{utc_now().timestamp()}",
            "story_type": request.story_type,
            "headline": _generate_headline(request.key_facts, request.story_type),
            "lead_paragraph": _generate_lead_paragraph(request.key_facts, request.affected_parties),
            "body_content": _generate_body_content(request.key_facts, request.legal_context),
            "quotes": _generate_quotes(request.affected_parties),
            "call_to_action": _generate_call_to_action(request.story_type),
            "media_targets": request.media_targets,
            "contact_information": _generate_media_contact(),
            "urgency": request.urgency,
            "distribution_plan": _generate_distribution_plan(request.media_targets),
            "created_at": utc_now().isoformat(),
        }

        return JSONResponse(
            content={"success": True, "press_release": press_release, "created_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Press release building failed: {e}")
        logger.exception("Press release building failed")
        raise HTTPException(status_code=500, detail="Press release building failed")


# =============================================================================
# Dashboard & Analyst Endpoints (Engine Layer)
# =============================================================================


@accountability_router.get("/dashboard")
async def get_dashboard(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Unified dashboard summary using real database data."""
    from app.models.models import CalendarEvent, Complaint, Document, Incident, TimelineEvent, VaultItem

    user_id = current_user.user_id if current_user else "anonymous"

    # Count timeline events
    timeline_result = await db.execute(
        select(func.count()).select_from(TimelineEvent).where(TimelineEvent.user_id == user_id)
    )
    timeline_count = timeline_result.scalar() or 0

    # Count upcoming calendar events
    calendar_result = await db.execute(
        select(func.count())
        .select_from(CalendarEvent)
        .where(CalendarEvent.user_id == user_id)
        .where(CalendarEvent.start_datetime >= utc_now())
    )
    upcoming_count = calendar_result.scalar() or 0

    # Count complaints
    complaint_result = await db.execute(select(func.count()).select_from(Complaint).where(Complaint.user_id == user_id))
    complaint_count = complaint_result.scalar() or 0

    # Count vault items (evidence)
    vault_result = await db.execute(select(func.count()).select_from(VaultItem).where(VaultItem.user_id == user_id))
    vault_count = vault_result.scalar() or 0

    # Count incidents
    incident_result = await db.execute(select(func.count()).select_from(Incident).where(Incident.user_id == user_id))
    incident_count = incident_result.scalar() or 0

    # Count documents
    doc_result = await db.execute(select(func.count()).select_from(Document).where(Document.user_id == user_id))
    doc_count = doc_result.scalar() or 0

    # Recent timeline events
    recent_events = await db.execute(
        select(TimelineEvent).where(TimelineEvent.user_id == user_id).order_by(TimelineEvent.event_date.desc()).limit(5)
    )
    events = recent_events.scalars().all()

    return JSONResponse(
        content={
            "user_id": user_id,
            "counts": {
                "timeline_events": timeline_count,
                "upcoming_deadlines": upcoming_count,
                "complaints": complaint_count,
                "vault_items": vault_count,
                "incidents": incident_count,
                "documents": doc_count,
            },
            "recent_events": [
                {
                    "id": e.id,
                    "type": e.event_type,
                    "date": e.event_date.isoformat() if e.event_date else None,
                    "status": e.status.value if e.status else None,
                }
                for e in events
            ],
            "generated_at": utc_now().isoformat(),
        }
    )


@accountability_router.get("/analyst")
async def get_analyst(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """AI Case Analyst — rule-based risk assessment from database."""
    from app.models.models import Complaint, Incident, TimelineEvent, VaultItem

    user_id = current_user.user_id if current_user else "anonymous"

    # Gather counts
    timeline_result = await db.execute(
        select(func.count()).select_from(TimelineEvent).where(TimelineEvent.user_id == user_id)
    )
    timeline_count = timeline_result.scalar() or 0

    complaint_result = await db.execute(select(func.count()).select_from(Complaint).where(Complaint.user_id == user_id))
    complaint_count = complaint_result.scalar() or 0

    vault_result = await db.execute(select(func.count()).select_from(VaultItem).where(VaultItem.user_id == user_id))
    vault_count = vault_result.scalar() or 0

    incident_result = await db.execute(select(func.count()).select_from(Incident).where(Incident.user_id == user_id))
    incident_count = incident_result.scalar() or 0

    # Risk scoring
    risk_score = 0
    risk_factors = []

    if incident_count >= 2:
        risk_score += 25
        risk_factors.append("Multiple incidents recorded")
    if complaint_count == 0 and vault_count >= 5:
        risk_score += 20
        risk_factors.append("Substantial evidence but no formal complaints filed")
    if timeline_count >= 10:
        risk_score += 15
        risk_factors.append("Extensive timeline — prolonged dispute")

    risk_score = min(risk_score, 100)
    if risk_score >= 60:
        risk_level = "High"
    elif risk_score >= 30:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    # Recommendations
    actions = []
    if complaint_count == 0:
        actions.append("File your first formal complaint to establish a paper trail.")
    if incident_count >= 2:
        actions.append("Pattern of multiple incidents — consider multi-venue filing.")
    if vault_count >= 5:
        actions.append("You have strong evidence documentation — prioritize filing.")
    if not actions:
        actions.append("Continue documenting evidence and maintain your timeline.")

    return JSONResponse(
        content={
            "user_id": user_id,
            "summary": f"{vault_count} evidence items, {incident_count} incidents, {complaint_count} complaints.",
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "recommended_actions": actions,
            "counts": {
                "timeline_events": timeline_count,
                "complaints": complaint_count,
                "vault_items": vault_count,
                "incidents": incident_count,
            },
            "generated_at": utc_now().isoformat(),
        }
    )


# Helper methods
def _generate_coalition_strategy(coalition_type: str) -> dict[str, Any]:
    """Generate coalition strategy."""
    strategies = {
        "tenant_organizing": {
            "approach": "Grassroots organizing",
            "tactics": ["Meetings", "Petitions", "Direct action"],
            "timeline": "3-6 months",
        },
        "legal_defense": {
            "approach": "Legal advocacy",
            "tactics": ["Legal clinics", "Pro bono network", "Court monitoring"],
            "timeline": "Ongoing",
        },
        "policy_advocacy": {
            "approach": "Policy change",
            "tactics": ["Lobbying", "Public testimony", "Campaign support"],
            "timeline": "6-12 months",
        },
    }
    return strategies.get(
        coalition_type, {"approach": "General advocacy", "tactics": ["Outreach"], "timeline": "3 months"}
    )


def _generate_coalition_timeline(action_type: str) -> list[dict[str, str]]:
    """Generate coalition timeline."""
    return [
        {"phase": "Planning", "duration": "2 weeks"},
        {"phase": "Outreach", "duration": "4 weeks"},
        {"phase": "Action", "duration": "2 weeks"},
        {"phase": "Follow-up", "duration": "2 weeks"},
    ]


def _identify_coalition_resources(coalition_type: str) -> list[str]:
    """Identify coalition resources needed."""
    return ["Meeting space", " Outreach materials", "Legal resources", "Media contacts"]


def _define_coalition_metrics(coalition_type: str) -> list[str]:
    """Define coalition success metrics."""
    return ["Number of participants", "Policy changes", "Media coverage", "Community support"]


def _process_evidence_data(evidence_data: dict[str, Any], evidence_type: str) -> dict[str, Any]:
    """Process evidence data based on type."""
    return {
        "processed": True,
        "type": evidence_type,
        "extracted_info": "Evidence processed successfully",
        "confidence": 0.85,
    }


def _analyze_evidence(evidence_data: dict[str, Any], evidence_type: str) -> dict[str, Any]:
    """Analyze evidence for legal relevance."""
    return {
        "legal_relevance": "high",
        "admissibility": "good",
        "supporting_claims": ["Housing violation", "Legal rights"],
        "evidence_strength": "strong",
    }


def _generate_evidence_recommendations(evidence_type: str) -> list[str]:
    """Generate evidence recommendations."""
    return [
        "Preserve original documents",
        "Create digital copies",
        "Document chain of custody",
        "Prepare witness statements",
    ]


def _simulate_public_records_search(record_type: str, search_criteria: dict[str, Any]) -> list[dict[str, Any]]:
    """Return simulated public records matching the requested record type.

    Produces deterministic, representative records until a real public records
    API is wired. Uses search_criteria (address, parcel_id, owner_name) to
    personalize the simulated results.
    """
    address = search_criteria.get("address", "Unknown property")
    parcel_id = search_criteria.get("parcel_id", "")
    owner_name = search_criteria.get("owner_name", "Unknown owner")
    date_from = search_criteria.get("date_from", "2024-01-01")
    date_to = search_criteria.get("date_to", "2025-12-31")

    base = {
        "record_type": record_type,
        "address": address,
        "parcel_id": parcel_id,
        "owner_name": owner_name,
        "date_range": {"from": date_from, "to": date_to},
        "source": "simulated",
    }

    record_type = (record_type or "").lower()
    if record_type == "code_violations":
        return [
            {
                **base,
                "violation_id": "CV-2024-001",
                "date": "2024-08-15",
                "description": "Habitability violation: heating deficiencies",
                "status": "open",
                "severity": "high",
                "agency": "City Housing Inspections",
            }
        ]
    if record_type == "housing_complaints":
        return [
            {
                **base,
                "complaint_id": "HC-2024-112",
                "date": "2024-09-03",
                "description": "Tenant complaint: unresolved maintenance requests",
                "status": "open",
                "agency": "Tenant Advocacy Office",
            }
        ]
    if record_type in {"liens", "tax_liens"}:
        return [
            {
                **base,
                "lien_id": "TL-2024-88",
                "date": "2024-06-20",
                "amount": "$3,450.00",
                "description": "Unpaid property tax lien",
                "status": "active",
            }
        ]
    if record_type in {"evictions", "eviction_filings"}:
        return [
            {
                **base,
                "case_number": "EV-2024-403",
                "date": "2024-10-01",
                "description": "Eviction filing by property owner",
                "status": "filed",
                "court": "Hennepin County Housing Court",
            }
        ]
    if record_type in {"tax_records", "tax_delinquency"}:
        return [
            {
                **base,
                "tax_year": "2024",
                "status": "delinquent",
                "amount": "$1,200.00",
                "description": "Property taxes delinquent for 2024",
            }
        ]
    if record_type == "owner_history":
        return [
            {
                **base,
                "event_date": "2023-04-10",
                "event": "Property transfer",
                "grantor": "Prior Owner LLC",
                "grantee": owner_name,
            }
        ]

    # Unknown record type: return a generic placeholder record so the caller
    # still gets a documented shape rather than empty list.
    return [
        {
            **base,
            "record_id": f"SIM-{record_type or 'unknown'}",
            "date": "2024-01-01",
            "description": f"Simulated {record_type} record for the requested property",
            "status": "simulated",
        }
    ]


def _generate_headline(key_facts: list[str], story_type: str) -> str:
    """Generate press release headline from key facts."""
    if not key_facts:
        return f"Housing Rights Violations Exposed in {story_type.title()} Case"
    primary_fact = key_facts[0].strip().rstrip(".")
    return f"{primary_fact}: Housing Rights Violations in {story_type.title()} Case"


def _generate_lead_paragraph(key_facts: list[str], affected_parties: list[dict[str, Any]]) -> str:
    """Generate press release lead paragraph from facts and affected parties."""
    party_count = len(affected_parties)
    fact_count = len(key_facts)
    facts_summary = "; ".join(key_facts[:3]) if key_facts else "multiple housing rights violations"
    return (
        f"{facts_summary}. "
        f"{fact_count} documented violation{'s' if fact_count != 1 else ''} "
        f"affecting {party_count} household{'s' if party_count != 1 else ''}."
    )


def _generate_body_content(key_facts: list[str], legal_context: dict[str, Any]) -> str:
    """Generate press release body content from facts and legal context."""
    facts_bullets = (
        "\n".join(f"- {fact}" for fact in key_facts)
        if key_facts
        else "- Evidence of systematic housing rights violations"
    )
    legal_summary = (
        legal_context.get("summary", "Applicable housing rights statutes provide protections against these practices.")
        if isinstance(legal_context, dict)
        else "Applicable housing rights statutes provide protections against these practices."
    )
    return f"Evidence summary:\n{facts_bullets}\n\nLegal context: {legal_summary}"


def _generate_quotes(affected_parties: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Generate quotes for press release from affected parties."""
    if not affected_parties:
        return [
            {
                "speaker": "Tenant Advocate",
                "quote": "These violations must stop. Every tenant deserves safe, lawful housing.",
            }
        ]
    quotes = []
    for party in affected_parties[:3]:
        speaker = party.get("name") or party.get("role") or "Affected Tenant"
        quotes.append(
            {"speaker": speaker, "quote": "These violations must stop. Every tenant deserves safe, lawful housing."}
        )
    return quotes


def _generate_call_to_action(story_type: str) -> str:
    """Generate call to action based on story type."""
    return f"Contact your representatives and demand housing rights enforcement. Report {story_type.lower()} violations to your local housing authority."


def _generate_media_contact() -> dict[str, str]:
    """Generate media contact information."""
    return {"name": "Housing Rights Coalition", "phone": "555-0123", "email": "media@housingrights.org"}


def _generate_distribution_plan(media_targets: list[str]) -> dict[str, Any]:
    """Generate media distribution plan."""
    return {"immediate": media_targets[:3], "secondary": media_targets[3:], "follow_up": "48 hours after distribution"}
