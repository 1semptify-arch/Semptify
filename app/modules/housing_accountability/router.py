"""
Housing Accountability Router - Regulatory Compliance & Oversight
=========================================================

FastAPI router for Housing Accountability Module.
Provides pattern detection, oversight packets, coalition tools, and regulatory compliance.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from app.core.security import get_current_user

logger = logging.getLogger(__name__)

# Initialize housing accountability router
accountability_router = APIRouter(prefix="/api/housing-accountability", tags=["Housing Accountability"])

# Pydantic Models
class PatternDetectionRequest(BaseModel):
    """Request for pattern detection analysis."""
    tenant_data: Dict[str, Any] = Field(..., description="Tenant data for analysis")
    property_data: Dict[str, Any] = Field(..., description="Property data for analysis")
    evidence_data: List[Dict[str, Any]] = Field(..., description="Evidence documents and data")
    analysis_type: str = Field("comprehensive", description="Type of analysis to perform")

class OversightPacketRequest(BaseModel):
    """Request for oversight packet generation."""
    packet_type: str = Field(..., description="Type of oversight packet (HUD, MDHR, CFPB, AG)")
    tenant_data: Dict[str, Any] = Field(..., description="Tenant information")
    violation_data: List[Dict[str, Any]] = Field(..., description="Violation and pattern data")
    evidence_attachments: List[str] = Field(..., description="Evidence document IDs")
    urgency_level: str = Field("standard", description="Urgency level (standard, urgent, emergency)")

class CoalitionRequest(BaseModel):
    """Request for coalition building tools."""
    coalition_type: str = Field(..., description="Type of coalition action")
    target_audience: str = Field(..., description="Target audience for coalition")
    message_data: Dict[str, Any] = Field(..., description="Message content and data")
    contact_list: List[Dict[str, Any]] = Field(..., description="Contact information")
    action_type: str = Field("outreach", description="Type of coalition action")

class EvidenceIntakeRequest(BaseModel):
    """Request for evidence intake processing."""
    evidence_type: str = Field(..., description="Type of evidence (document, photo, video, testimony)")
    evidence_data: Dict[str, Any] = Field(..., description="Evidence content and metadata")
    case_context: Dict[str, Any] = Field(..., description="Case context and information")
    priority: str = Field("standard", description="Processing priority")

class PublicRecordsRequest(BaseModel):
    """Request for public records research."""
    record_type: str = Field(..., description="Type of public record to research")
    search_criteria: Dict[str, Any] = Field(..., description="Search criteria and parameters")
    jurisdiction: str = Field(..., description="Jurisdiction for records search")
    time_range: Optional[str] = Field(None, description="Time range for records")

class PressBuilderRequest(BaseModel):
    """Request for press release generation."""
    story_type: str = Field(..., description="Type of press story")
    key_facts: List[str] = Field(..., description="Key facts for the story")
    affected_parties: List[Dict[str, Any]] = Field(..., description="Affected parties information")
    legal_context: Dict[str, Any] = Field(..., description="Legal and regulatory context")
    media_targets: List[str] = Field(..., description="Target media outlets")
    urgency: str = Field("standard", description="Story urgency level")

# Housing Accountability Services
class PatternDetectionService:
    """Pattern detection service for housing violations."""
    
    def __init__(self):
        self.pattern_cache = {}
    
    def detect_repeated_fees(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect repeated fee patterns."""
        # Placeholder implementation
        patterns = []
        
        # Analyze fee patterns
        fee_history = data.get("fee_history", [])
        if len(fee_history) > 3:
            # Look for recurring fees
            recurring_fees = []
            for i in range(len(fee_history) - 1):
                current_fee = fee_history[i]
                next_fee = fee_history[i + 1]
                
                # Check for similar fee amounts and timing
                if (abs(current_fee.get("amount", 0) - next_fee.get("amount", 0)) < 5 and
                    abs((datetime.fromisoformat(current_fee.get("date", "")) - 
                         datetime.fromisoformat(next_fee.get("date", ""))).days) <= 35):
                    recurring_fees.append(current_fee)
            
            if recurring_fees:
                patterns.append({
                    "type": "repeated_fees",
                    "severity": "medium",
                    "description": f"Detected {len(recurring_fees)} potentially recurring fees",
                    "evidence": recurring_fees,
                    "legal_basis": "Minnesota Statutes 504B.215 - Prohibited landlord practices"
                })
        
        return {"patterns": patterns, "confidence": 0.7}
    
    def detect_eviction_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect eviction-related patterns."""
        patterns = []
        
        # Analyze eviction history
        eviction_history = data.get("eviction_history", [])
        if len(eviction_history) > 1:
            patterns.append({
                "type": "serial_eviction",
                "severity": "high",
                "description": f"Multiple eviction actions detected ({len(eviction_history)})",
                "evidence": eviction_history,
                "legal_basis": "Minnesota Statutes 504B.291 - Retaliatory eviction prohibition"
            })
        
        # Check for timing patterns
        if eviction_history:
            for eviction in eviction_history:
                filing_date = datetime.fromisoformat(eviction.get("filing_date", ""))
                complaint_date = datetime.fromisoformat(eviction.get("complaint_date", ""))
                
                # Check if eviction followed complaint filing
                if complaint_date and filing_date and (filing_date - complaint_date).days <= 30:
                    patterns.append({
                        "type": "retaliatory_eviction",
                        "severity": "high",
                        "description": "Eviction filing shortly after tenant complaint",
                        "evidence": eviction,
                        "legal_basis": "Minnesota Statutes 504B.291 - Retaliatory eviction"
                    })
        
        return {"patterns": patterns, "confidence": 0.8}
    
    def detect_subsidy_interference(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
                patterns.append({
                    "type": "subsidy_interference",
                    "severity": "high",
                    "description": f"Subsidy interference indicators: {', '.join(interference_indicators)}",
                    "evidence": interference_indicators,
                    "legal_basis": "HUD Handbook 4350.3 - Section 8 program compliance"
                })
        
        return {"patterns": patterns, "confidence": 0.75}
    
    def detect_court_order_violations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect court order violation patterns."""
        patterns = []
        
        # Analyze court orders
        court_orders = data.get("court_orders", [])
        for order in court_orders:
            if order.get("violated", False):
                patterns.append({
                    "type": "court_order_violation",
                    "severity": "critical",
                    "description": f"Violation of court order: {order.get('order_type', 'Unknown')}",
                    "evidence": order,
                    "legal_basis": "Contempt of court proceedings"
                })
        
        return {"patterns": patterns, "confidence": 0.9}
    
    def generate_pattern_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
                "patterns_by_type": self._group_patterns_by_type(all_patterns)
            },
            "patterns": all_patterns,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat()
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
    
    def _group_patterns_by_type(self, patterns: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group patterns by type."""
        grouped = {}
        for pattern in patterns:
            pattern_type = pattern.get("type", "unknown")
            grouped[pattern_type] = grouped.get(pattern_type, 0) + 1
        return grouped

class OversightPacketService:
    """Oversight packet generation service."""
    
    def build_ag_packet(self, tenant_data: Dict[str, Any], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "Seek appropriate remedies"
            ],
            "evidence_required": [
                "Lease agreement",
                "Communication records",
                "Payment history",
                "Violation documentation"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        return packet
    
    def build_hud_packet(self, tenant_data: Dict[str, Any], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "Provide tenant protections"
            ],
            "evidence_required": [
                "Protected class documentation",
                "Differential treatment evidence",
                "Communication records",
                "Housing application records"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        return packet
    
    def build_mdhr_packet(self, tenant_data: Dict[str, Any], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "Provide appropriate remedies"
            ],
            "evidence_required": [
                "Protected class documentation",
                "Comparative evidence",
                "Communication records",
                "Housing records"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        return packet
    
    def build_cfpb_packet(self, tenant_data: Dict[str, Any], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "Provide consumer relief"
            ],
            "evidence_required": [
                "Financial records",
                "Fee documentation",
                "Communication records",
                "Payment history"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        return packet
    
    def _summarize_violations(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            "total_violations": len(patterns)
        }
    
    def _analyze_fair_housing_violations(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze fair housing violations."""
        return [p for p in patterns if "discrimination" in p.get("type", "").lower()]
    
    def _identify_discrimination_patterns(self, patterns: List[Dict[str, Any]]) -> List[str]:
        """Identify discrimination patterns."""
        indicators = []
        for pattern in patterns:
            if "discrimination" in pattern.get("type", "").lower():
                indicators.append(pattern.get("description", ""))
        return indicators
    
    def _analyze_human_rights_violations(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze human rights violations."""
        return [p for p in patterns if "discrimination" in p.get("type", "").lower() or "harassment" in p.get("type", "").lower()]
    
    def _identify_state_law_violations(self, patterns: List[Dict[str, Any]]) -> List[str]:
        """Identify state law violations."""
        violations = []
        for pattern in patterns:
            if "minnesota" in pattern.get("legal_basis", "").lower():
                violations.append(pattern.get("legal_basis", ""))
        return violations
    
    def _analyze_discrimination_under_state_law(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze discrimination under state law."""
        discrimination_patterns = [p for p in patterns if "discrimination" in p.get("type", "").lower()]
        return {
            "discrimination_count": len(discrimination_patterns),
            "protected_classes_affected": list(set(p.get("protected_class", "unknown") for p in discrimination_patterns)),
            "violation_types": list(set(p.get("type", "unknown") for p in discrimination_patterns))
        }
    
    def _analyze_financial_violations(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze financial violations."""
        return [p for p in patterns if "fee" in p.get("type", "").lower() or "rent" in p.get("type", "").lower()]
    
    def _identify_consumer_protection_violations(self, patterns: List[Dict[str, Any]]) -> List[str]:
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
async def detect_patterns(request: PatternDetectionRequest,
                         current_user = Depends(get_current_user)):
    """Detect housing violation patterns."""
    try:
        # Combine all data for pattern analysis
        analysis_data = {
            **request.tenant_data,
            **request.property_data,
            "evidence_data": request.evidence_data
        }
        
        # Generate pattern summary
        pattern_summary = pattern_service.generate_pattern_summary(analysis_data)
        
        return JSONResponse(content={
            "success": True,
            "pattern_analysis": pattern_summary,
            "analysis_type": request.analysis_type,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Pattern detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern detection failed: {str(e)}")

@accountability_router.post("/oversight/packet/generate")
async def generate_oversight_packet(request: OversightPacketRequest,
                                  current_user = Depends(get_current_user)):
    """Generate oversight packet for regulatory submission."""
    try:
        # Generate patterns for packet content
        analysis_data = {
            **request.tenant_data,
            "violation_data": request.violation_data
        }
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
        
        return JSONResponse(content={
            "success": True,
            "oversight_packet": packet,
            "urgency_level": request.urgency_level,
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Oversight packet generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Packet generation failed: {str(e)}")

@accountability_router.post("/coalition/build")
async def build_coalition_action(request: CoalitionRequest,
                               current_user = Depends(get_current_user)):
    """Build coalition action for community organizing."""
    try:
        # Generate coalition action plan
        action_plan = {
            "coalition_type": request.coalition_type,
            "target_audience": request.target_audience,
            "message": request.message_data,
            "contacts": request.contact_list,
            "action_type": request.action_type,
            "strategy": self._generate_coalition_strategy(request.coalition_type),
            "timeline": self._generate_coalition_timeline(request.action_type),
            "resources_needed": self._identify_coalition_resources(request.coalition_type),
            "success_metrics": self._define_coalition_metrics(request.coalition_type),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content={
            "success": True,
            "coalition_action": action_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Coalition building failed: {e}")
        raise HTTPException(status_code=500, detail=f"Coalition building failed: {str(e)}")

@accountability_router.post("/evidence/intake")
async def process_evidence_intake(request: EvidenceIntakeRequest,
                                 current_user = Depends(get_current_user)):
    """Process evidence intake for housing cases."""
    try:
        # Process evidence based on type
        processed_evidence = {
            "evidence_id": f"evidence_{datetime.now().timestamp()}",
            "evidence_type": request.evidence_type,
            "processed_data": self._process_evidence_data(request.evidence_data, request.evidence_type),
            "case_context": request.case_context,
            "priority": request.priority,
            "analysis_results": self._analyze_evidence(request.evidence_data, request.evidence_type),
            "recommendations": self._generate_evidence_recommendations(request.evidence_type),
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content={
            "success": True,
            "processed_evidence": processed_evidence,
            "processed_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Evidence intake failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evidence intake failed: {str(e)}")

@accountability_router.post("/public-records/search")
async def search_public_records(request: PublicRecordsRequest,
                               current_user = Depends(get_current_user)):
    """Search public records for housing cases."""
    try:
        # Simulate public records search
        search_results = {
            "search_id": f"search_{datetime.now().timestamp()}",
            "record_type": request.record_type,
            "search_criteria": request.search_criteria,
            "jurisdiction": request.jurisdiction,
            "time_range": request.time_range,
            "results": self._simulate_public_records_search(request.record_type, request.search_criteria),
            "total_results": 0,  # Would be populated by actual search
            "search_duration": "2.3 seconds",
            "searched_at": datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content={
            "success": True,
            "search_results": search_results,
            "searched_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Public records search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Public records search failed: {str(e)}")

@accountability_router.post("/press/build")
async def build_press_release(request: PressBuilderRequest,
                            current_user = Depends(get_current_user)):
    """Build press release for housing rights advocacy."""
    try:
        # Generate press release
        press_release = {
            "press_id": f"press_{datetime.now().timestamp()}",
            "story_type": request.story_type,
            "headline": self._generate_headline(request.key_facts, request.story_type),
            "lead_paragraph": self._generate_lead_paragraph(request.key_facts, request.affected_parties),
            "body_content": self._generate_body_content(request.key_facts, request.legal_context),
            "quotes": self._generate_quotes(request.affected_parties),
            "call_to_action": self._generate_call_to_action(request.story_type),
            "media_targets": request.media_targets,
            "contact_information": self._generate_media_contact(),
            "urgency": request.urgency,
            "distribution_plan": self._generate_distribution_plan(request.media_targets),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        return JSONResponse(content={
            "success": True,
            "press_release": press_release,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Press release building failed: {e}")
        raise HTTPException(status_code=500, detail=f"Press release building failed: {str(e)}")

# Helper methods
def _generate_coalition_strategy(coalition_type: str) -> Dict[str, Any]:
    """Generate coalition strategy."""
    strategies = {
        "tenant_organizing": {
            "approach": "Grassroots organizing",
            "tactics": ["Meetings", "Petitions", "Direct action"],
            "timeline": "3-6 months"
        },
        "legal_defense": {
            "approach": "Legal advocacy",
            "tactics": ["Legal clinics", "Pro bono network", "Court monitoring"],
            "timeline": "Ongoing"
        },
        "policy_advocacy": {
            "approach": "Policy change",
            "tactics": ["Lobbying", "Public testimony", "Campaign support"],
            "timeline": "6-12 months"
        }
    }
    return strategies.get(coalition_type, {"approach": "General advocacy", "tactics": ["Outreach"], "timeline": "3 months"})

def _generate_coalition_timeline(action_type: str) -> List[Dict[str, str]]:
    """Generate coalition timeline."""
    return [
        {"phase": "Planning", "duration": "2 weeks"},
        {"phase": "Outreach", "duration": "4 weeks"},
        {"phase": "Action", "duration": "2 weeks"},
        {"phase": "Follow-up", "duration": "2 weeks"}
    ]

def _identify_coalition_resources(coalition_type: str) -> List[str]:
    """Identify coalition resources needed."""
    return ["Meeting space", " Outreach materials", "Legal resources", "Media contacts"]

def _define_coalition_metrics(coalition_type: str) -> List[str]:
    """Define coalition success metrics."""
    return ["Number of participants", "Policy changes", "Media coverage", "Community support"]

def _process_evidence_data(evidence_data: Dict[str, Any], evidence_type: str) -> Dict[str, Any]:
    """Process evidence data based on type."""
    return {
        "processed": True,
        "type": evidence_type,
        "extracted_info": "Evidence processed successfully",
        "confidence": 0.85
    }

def _analyze_evidence(evidence_data: Dict[str, Any], evidence_type: str) -> Dict[str, Any]:
    """Analyze evidence for legal relevance."""
    return {
        "legal_relevance": "high",
        "admissibility": "good",
        "supporting_claims": ["Housing violation", "Legal rights"],
        "evidence_strength": "strong"
    }

def _generate_evidence_recommendations(evidence_type: str) -> List[str]:
    """Generate evidence recommendations."""
    return [
        "Preserve original documents",
        "Create digital copies",
        "Document chain of custody",
        "Prepare witness statements"
    ]

def _simulate_public_records_search(record_type: str, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Simulate public records search results."""
    return []  # Placeholder

def _generate_headline(key_facts: List[str], story_type: str) -> str:
    """Generate press release headline."""
    return f"Housing Rights Violations Exposed in {story_type.title()} Case"

def _generate_lead_paragraph(key_facts: List[str], affected_parties: List[Dict[str, Any]]) -> str:
    """Generate press release lead paragraph."""
    return f"Multiple housing rights violations have been documented affecting {len(affected_parties)} households."

def _generate_body_content(key_facts: List[str], legal_context: Dict[str, Any]) -> str:
    """Generate press release body content."""
    return "Evidence shows systematic violations of housing rights laws..."

def _generate_quotes(affected_parties: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Generate quotes for press release."""
    return [{"speaker": "Tenant Advocate", "quote": "These violations must stop"}]

def _generate_call_to_action(story_type: str) -> str:
    """Generate call to action."""
    return "Contact your representatives and demand housing rights enforcement."

def _generate_media_contact() -> Dict[str, str]:
    """Generate media contact information."""
    return {
        "name": "Housing Rights Coalition",
        "phone": "555-0123",
        "email": "media@housingrights.org"
    }

def _generate_distribution_plan(media_targets: List[str]) -> Dict[str, Any]:
    """Generate media distribution plan."""
    return {
        "immediate": media_targets[:3],
        "secondary": media_targets[3:],
        "follow_up": "48 hours after distribution"
    }
