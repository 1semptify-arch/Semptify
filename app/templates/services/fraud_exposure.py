"""
Fraud Exposure Module - Tenant Rights Fraud Analysis
====================================================

Analyzes landlord fraud patterns including:
- Subsidy fraud (Section 8, LIHTC, etc.)
- Lender fraud (FHA, Fannie Mae violations)
- Document fraud (forged signatures, missing docs)
- Code violations with continued rent collection
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FraudType(str, Enum):
    """Types of fraud that can be detected"""
    SUBSIDY_FRAUD = "subsidy_fraud"
    LENDER_FRAUD = "lender_fraud"
    DOCUMENT_FRAUD = "document_fraud"
    HABITABILITY_FRAUD = "habitability_fraud"
    RENT_OVERCHARGE = "rent_overcharge"
    ILLEGAL_FEES = "illegal_fees"
    RETALIATION = "retaliation"
    DISCRIMINATION = "discrimination"


class SeverityLevel(str, Enum):
    """Severity of fraud finding"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FraudFinding:
    """Individual fraud finding"""
    id: str
    fraud_type: FraudType
    severity: SeverityLevel
    rule: str
    description: str
    evidence: List[str] = field(default_factory=list)
    affected_parties: List[str] = field(default_factory=list)
    potential_damages: Optional[float] = None
    reporting_agencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fraud_type": self.fraud_type.value,
            "severity": self.severity.value,
            "rule": self.rule,
            "description": self.description,
            "evidence": self.evidence,
            "affected_parties": self.affected_parties,
            "potential_damages": self.potential_damages,
            "reporting_agencies": self.reporting_agencies,
        }


@dataclass
class FraudReport:
    """Complete fraud analysis report"""
    id: str
    landlord_id: str
    property_address: Optional[str]
    findings: List[FraudFinding]
    total_potential_damages: float
    risk_score: int  # 0-100
    created_at: datetime
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "landlord_id": self.landlord_id,
            "property_address": self.property_address,
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
            "total_potential_damages": self.total_potential_damages,
            "risk_score": self.risk_score,
            "created_at": self.created_at.isoformat(),
            "recommendations": self.recommendations,
        }


# Fraud detection rules
FRAUD_RULES = {
    "unsigned_documents": {
        "fraud_type": FraudType.DOCUMENT_FRAUD,
        "severity": SeverityLevel.HIGH,
        "description": "Legal documents lack required signatures",
        "reporting_agencies": ["MN Attorney General", "HUD OIG"],
    },
    "missing_habitability_cert": {
        "fraud_type": FraudType.HABITABILITY_FRAUD,
        "severity": SeverityLevel.CRITICAL,
        "description": "Property lacks certificate of habitability while collecting rent",
        "reporting_agencies": ["City Housing Inspector", "MN Attorney General"],
    },
    "section8_overcharge": {
        "fraud_type": FraudType.SUBSIDY_FRAUD,
        "severity": SeverityLevel.CRITICAL,
        "description": "Charging above HUD Fair Market Rent while receiving Section 8",
        "reporting_agencies": ["HUD OIG", "Local Housing Authority"],
    },
    "lihtc_income_violation": {
        "fraud_type": FraudType.SUBSIDY_FRAUD,
        "severity": SeverityLevel.HIGH,
        "description": "LIHTC property renting to over-income tenants",
        "reporting_agencies": ["IRS", "State Housing Finance Agency"],
    },
    "fha_maintenance_violation": {
        "fraud_type": FraudType.LENDER_FRAUD,
        "severity": SeverityLevel.HIGH,
        "description": "FHA-insured property not meeting maintenance standards",
        "reporting_agencies": ["HUD", "FHA"],
    },
    "code_violation_rent_collection": {
        "fraud_type": FraudType.HABITABILITY_FRAUD,
        "severity": SeverityLevel.HIGH,
        "description": "Collecting full rent despite unresolved code violations",
        "reporting_agencies": ["City Housing Inspector", "MN Attorney General"],
    },
    "illegal_late_fees": {
        "fraud_type": FraudType.ILLEGAL_FEES,
        "severity": SeverityLevel.MEDIUM,
        "description": "Late fees exceed 8% statutory maximum (MN)",
        "reporting_agencies": ["MN Attorney General"],
    },
    "retaliatory_eviction": {
        "fraud_type": FraudType.RETALIATION,
        "severity": SeverityLevel.HIGH,
        "description": "Eviction filed within 90 days of tenant complaint",
        "reporting_agencies": ["MN Attorney General", "Fair Housing Center"],
    },
    "discriminatory_practice": {
        "fraud_type": FraudType.DISCRIMINATION,
        "severity": SeverityLevel.CRITICAL,
        "description": "Evidence of discriminatory housing practices",
        "reporting_agencies": ["HUD FHEO", "MN Dept of Human Rights"],
    },
}


class FraudExposureService:
    """Service for analyzing landlord fraud patterns"""
    
    def __init__(self):
        self._reports: Dict[str, FraudReport] = {}
        logger.info("🔍 Fraud Exposure Service initialized")
    
    async def analyze_fraud(
        self,
        landlord_id: str,
        case_docs: List[Dict[str, Any]],
        subsidies: List[Dict[str, Any]],
        lenders: List[Dict[str, Any]],
        property_address: Optional[str] = None,
        code_violations: List[Dict[str, Any]] = None,
        rent_history: List[Dict[str, Any]] = None,
        complaint_history: List[Dict[str, Any]] = None,
    ) -> FraudReport:
        """
        Analyze case for potential fraud patterns.
        
        Args:
            landlord_id: Landlord identifier
            case_docs: List of case documents with metadata
            subsidies: List of subsidy programs (Section 8, LIHTC, etc.)
            lenders: List of lenders (FHA, Fannie Mae, etc.)
            property_address: Property address
            code_violations: List of code violations
            rent_history: Rent payment history
            complaint_history: History of tenant complaints
            
        Returns:
            FraudReport with findings
        """
        findings: List[FraudFinding] = []
        finding_id = 0
        
        # Check document fraud
        for doc in case_docs:
            if doc.get("signature_status") == "missing":
                finding_id += 1
                rule = FRAUD_RULES["unsigned_documents"]
                findings.append(FraudFinding(
                    id=f"f_{finding_id:03d}",
                    fraud_type=rule["fraud_type"],
                    severity=rule["severity"],
                    rule="unsigned_documents",
                    description=rule["description"],
                    evidence=[f"Document: {doc.get('name', 'Unknown')} missing signature"],
                    reporting_agencies=rule["reporting_agencies"],
                ))
        
        # Check subsidy fraud
        for subsidy in subsidies:
            subsidy_type = subsidy.get("type", "").lower()
            
            if "section 8" in subsidy_type or "section8" in subsidy_type:
                # Check for overcharges
                if subsidy.get("rent_charged", 0) > subsidy.get("fmr_limit", float('inf')):
                    finding_id += 1
                    rule = FRAUD_RULES["section8_overcharge"]
                    overcharge = subsidy.get("rent_charged", 0) - subsidy.get("fmr_limit", 0)
                    findings.append(FraudFinding(
                        id=f"f_{finding_id:03d}",
                        fraud_type=rule["fraud_type"],
                        severity=rule["severity"],
                        rule="section8_overcharge",
                        description=rule["description"],
                        evidence=[f"Rent ${subsidy.get('rent_charged')} exceeds FMR ${subsidy.get('fmr_limit')}"],
                        potential_damages=overcharge * 12 * 3,  # Triple damages for 1 year
                        reporting_agencies=rule["reporting_agencies"],
                    ))
            
            if "lihtc" in subsidy_type:
                if subsidy.get("income_violation"):
                    finding_id += 1
                    rule = FRAUD_RULES["lihtc_income_violation"]
                    findings.append(FraudFinding(
                        id=f"f_{finding_id:03d}",
                        fraud_type=rule["fraud_type"],
                        severity=rule["severity"],
                        rule="lihtc_income_violation",
                        description=rule["description"],
                        evidence=[subsidy.get("violation_details", "Income limit exceeded")],
                        reporting_agencies=rule["reporting_agencies"],
                    ))
        
        # Check lender fraud
        for lender in lenders:
            lender_type = lender.get("type", "").lower()
            
            if "fha" in lender_type:
                if lender.get("maintenance_issues"):
                    finding_id += 1
                    rule = FRAUD_RULES["fha_maintenance_violation"]
                    findings.append(FraudFinding(
                        id=f"f_{finding_id:03d}",
                        fraud_type=rule["fraud_type"],
                        severity=rule["severity"],
                        rule="fha_maintenance_violation",
                        description=rule["description"],
                        evidence=lender.get("maintenance_issues", []),
                        reporting_agencies=rule["reporting_agencies"],
                    ))
        
        # Check code violations
        if code_violations:
            unresolved = [v for v in code_violations if not v.get("resolved")]
            if unresolved and rent_history:
                # Check if rent was collected during violations
                finding_id += 1
                rule = FRAUD_RULES["code_violation_rent_collection"]
                findings.append(FraudFinding(
                    id=f"f_{finding_id:03d}",
                    fraud_type=rule["fraud_type"],
                    severity=rule["severity"],
                    rule="code_violation_rent_collection",
                    description=rule["description"],
                    evidence=[f"{len(unresolved)} unresolved code violations"],
                    reporting_agencies=rule["reporting_agencies"],
                ))
        
        # Check for retaliation
        if complaint_history:
            for complaint in complaint_history:
                complaint_date = complaint.get("date")
                eviction_date = complaint.get("eviction_filed_date")
                if complaint_date and eviction_date:
                    # Simple check - within 90 days
                    if complaint.get("days_to_eviction", 999) <= 90:
                        finding_id += 1
                        rule = FRAUD_RULES["retaliatory_eviction"]
                        findings.append(FraudFinding(
                            id=f"f_{finding_id:03d}",
                            fraud_type=rule["fraud_type"],
                            severity=rule["severity"],
                            rule="retaliatory_eviction",
                            description=rule["description"],
                            evidence=[f"Eviction filed {complaint.get('days_to_eviction')} days after complaint"],
                            reporting_agencies=rule["reporting_agencies"],
                        ))
        
        # Calculate totals
        total_damages = sum(f.potential_damages or 0 for f in findings)
        
        # Calculate risk score (0-100)
        risk_score = min(100, len(findings) * 15 + sum(
            30 if f.severity == SeverityLevel.CRITICAL else
            20 if f.severity == SeverityLevel.HIGH else
            10 if f.severity == SeverityLevel.MEDIUM else 5
            for f in findings
        ))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(findings)
        
        # Create report
        report_id = f"fr_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{landlord_id[:8]}"
        report = FraudReport(
            id=report_id,
            landlord_id=landlord_id,
            property_address=property_address,
            findings=findings,
            total_potential_damages=total_damages,
            risk_score=risk_score,
            created_at=datetime.now(timezone.utc),
            recommendations=recommendations,
        )
        
        self._reports[report_id] = report
        logger.info(f"🔍 Fraud analysis complete: {len(findings)} findings, risk score {risk_score}")
        
        return report
    
    def _generate_recommendations(self, findings: List[FraudFinding]) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        
        fraud_types = set(f.fraud_type for f in findings)
        agencies = set()
        for f in findings:
            agencies.update(f.reporting_agencies)
        
        if FraudType.SUBSIDY_FRAUD in fraud_types:
            recommendations.append("File complaint with HUD Office of Inspector General")
            recommendations.append("Contact local Housing Authority fraud hotline")
        
        if FraudType.DOCUMENT_FRAUD in fraud_types:
            recommendations.append("Request certified copies of all lease documents")
            recommendations.append("Consider reporting to MN Attorney General Consumer Division")
        
        if FraudType.HABITABILITY_FRAUD in fraud_types:
            recommendations.append("Request rent escrow through the court")
            recommendations.append("Document all habitability issues with photos/video")
        
        if FraudType.RETALIATION in fraud_types:
            recommendations.append("Raise retaliation as affirmative defense in eviction")
            recommendations.append("File complaint with MN Attorney General")
        
        if agencies:
            recommendations.append(f"Consider filing complaints with: {', '.join(sorted(agencies))}")
        
        return recommendations
    
    def get_report(self, report_id: str) -> Optional[FraudReport]:
        """Get a fraud report by ID"""
        return self._reports.get(report_id)
    
    def get_reports_for_landlord(self, landlord_id: str) -> List[FraudReport]:
        """Get all reports for a landlord"""
        return [r for r in self._reports.values() if r.landlord_id == landlord_id]

    def check_habitability_fraud(self, violations: List[Any]) -> Dict[str, Any]:
        """Check for habitability fraud based on violations"""
        findings = []
        for violation in violations:
            if isinstance(violation, dict):
                desc = violation.get("description", str(violation))
            else:
                desc = str(violation)
            findings.append({
                "type": "habitability",
                "description": desc,
                "severity": "high" if "health" in desc.lower() or "safety" in desc.lower() else "medium"
            })
        
        return {
            "fraud_detected": len(findings) > 0,
            "findings": findings,
            "risk_level": "high" if len(findings) >= 3 else "medium" if len(findings) >= 1 else "low",
            "recommendations": [
                "Document all violations with photos",
                "Request rent escrow if violations persist",
                "Report to city housing inspector"
            ] if findings else []
        }

    def check_hud_subsidy_fraud(self, subsidy_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Check for HUD/Section 8 subsidy fraud"""
        if not subsidy_info:
            return {"fraud_detected": False, "findings": [], "risk_level": "low"}
        
        findings = []
        
        # Check rent overcharge
        rent_charged = subsidy_info.get("rent_charged", 0)
        fmr_limit = subsidy_info.get("fmr_limit", 0)
        if rent_charged > fmr_limit > 0:
            findings.append({
                "type": "section8_overcharge",
                "description": f"Rent ${rent_charged} exceeds FMR limit ${fmr_limit}",
                "severity": "critical",
                "potential_damages": (rent_charged - fmr_limit) * 12 * 3
            })
        
        # Check inspection failures
        if subsidy_info.get("failed_inspection"):
            findings.append({
                "type": "inspection_fraud",
                "description": "Collecting subsidy while failing HQS inspection",
                "severity": "high"
            })
        
        return {
            "fraud_detected": len(findings) > 0,
            "findings": findings,
            "risk_level": "critical" if any(f.get("severity") == "critical" for f in findings) else "high" if findings else "low",
            "reporting_agencies": ["HUD OIG", "Local Housing Authority"] if findings else [],
            "recommendations": [
                "Report to HUD Office of Inspector General: 1-800-347-3735",
                "File complaint with local Housing Authority",
                "Document all rent payments and subsidy amounts"
            ] if findings else []
        }

    def check_mortgage_fraud(self, lender_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Check for mortgage/lender fraud"""
        if not lender_info:
            return {"fraud_detected": False, "findings": [], "risk_level": "low"}
        
        findings = []
        lender_type = lender_info.get("type", "").lower()
        
        # FHA violations
        if "fha" in lender_type:
            if lender_info.get("maintenance_issues"):
                findings.append({
                    "type": "fha_maintenance_violation",
                    "description": "FHA property not meeting maintenance standards",
                    "severity": "high",
                    "issues": lender_info.get("maintenance_issues", [])
                })
        
        # Fannie Mae violations
        if "fannie" in lender_type or "freddie" in lender_type:
            if lender_info.get("code_violations"):
                findings.append({
                    "type": "gse_code_violation",
                    "description": "GSE-backed property with unresolved code violations",
                    "severity": "high"
                })
        
        return {
            "fraud_detected": len(findings) > 0,
            "findings": findings,
            "risk_level": "high" if findings else "low",
            "reporting_agencies": ["HUD", "CFPB", "State AG"] if findings else []
        }

    def check_security_deposit_fraud(
        self,
        deposit_amount: Optional[float],
        rent_amount: Optional[float],
        deductions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Check for security deposit fraud"""
        findings = []
        
        # Check if deposit exceeds legal limit (1 month in MN)
        if deposit_amount and rent_amount and deposit_amount > rent_amount:
            findings.append({
                "type": "excessive_deposit",
                "description": f"Security deposit ${deposit_amount} exceeds 1 month rent ${rent_amount}",
                "severity": "medium",
                "statute": "Minn. Stat. § 504B.178"
            })
        
        # Check deductions
        if deductions:
            total_deductions = sum(d.get("amount", 0) for d in deductions)
            if deposit_amount and total_deductions > deposit_amount:
                findings.append({
                    "type": "excessive_deductions",
                    "description": f"Deductions ${total_deductions} exceed deposit ${deposit_amount}",
                    "severity": "high"
                })
            
            # Check for normal wear and tear charges
            wear_tear_keywords = ["paint", "carpet wear", "normal", "cleaning"]
            for d in deductions:
                desc = d.get("description", "").lower()
                if any(kw in desc for kw in wear_tear_keywords):
                    findings.append({
                        "type": "improper_deduction",
                        "description": f"Potentially improper deduction for normal wear: {d.get('description')}",
                        "severity": "medium"
                    })
        
        return {
            "fraud_detected": len(findings) > 0,
            "findings": findings,
            "risk_level": "high" if any(f.get("severity") == "high" for f in findings) else "medium" if findings else "low",
            "recommendations": [
                "Send demand letter for deposit return",
                "File in conciliation court within 2 years",
                "Request itemized deduction list"
            ] if findings else []
        }

    def get_statute_of_limitations(
        self,
        fraud_type: str,
        discovery_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statute of limitations info for fraud type"""
        sol_info = {
            "habitability": {
                "civil_action": "6 years",
                "criminal": "3 years",
                "statute": "Minn. Stat. § 541.05",
                "notes": "Runs from date of discovery for fraud"
            },
            "hud": {
                "civil_action": "6 years",
                "criminal": "5 years",
                "statute": "31 U.S.C. § 3731 (False Claims Act)",
                "notes": "Whistleblower can receive 15-30% of recovery",
                "federal_hotline": "1-800-347-3735"
            },
            "mortgage": {
                "civil_action": "6 years",
                "criminal": "10 years",
                "statute": "18 U.S.C. § 1014",
                "notes": "Bank fraud has extended limitations"
            },
            "security_deposit": {
                "civil_action": "2 years",
                "statute": "Minn. Stat. § 504B.178",
                "notes": "Must demand return within 21 days of move-out"
            },
            "discrimination": {
                "hud_complaint": "1 year",
                "civil_action": "2 years",
                "statute": "42 U.S.C. § 3613",
                "notes": "File with HUD FHEO within 1 year"
            }
        }
        
        fraud_key = fraud_type.lower().replace("_fraud", "").replace("fraud_", "")
        info = sol_info.get(fraud_key, {
            "civil_action": "6 years (general)",
            "notes": "Consult attorney for specific fraud type"
        })
        
        result = {
            "fraud_type": fraud_type,
            "limitations": info,
            "discovery_date": discovery_date
        }
        
        if discovery_date:
            result["note"] = "Statute may be tolled until date of discovery for fraud claims"
        
        return result

    def get_whistleblower_protections(self, fraud_type: Optional[str] = None) -> Dict[str, Any]:
        """Get whistleblower protection information"""
        protections = {
            "federal": {
                "false_claims_act": {
                    "statute": "31 U.S.C. § 3730",
                    "protection": "Protection from retaliation for reporting fraud against government",
                    "reward": "15-30% of recovered funds",
                    "applies_to": ["HUD fraud", "Section 8 fraud", "FHA fraud"]
                },
                "hud_oig": {
                    "hotline": "1-800-347-3735",
                    "online": "https://www.hudoig.gov/hotline",
                    "protection": "Anonymous reporting available"
                }
            },
            "minnesota": {
                "whistleblower_act": {
                    "statute": "Minn. Stat. § 181.932",
                    "protection": "Cannot be terminated for reporting violations",
                    "remedies": ["Reinstatement", "Back pay", "Attorney fees"]
                },
                "tenant_retaliation": {
                    "statute": "Minn. Stat. § 504B.285",
                    "protection": "Landlord cannot retaliate for complaints",
                    "safe_harbor": "90 days after good-faith report"
                }
            },
            "reporting_tips": [
                "Document everything with dates and photos",
                "Report to multiple agencies simultaneously",
                "Keep copies of all communications",
                "Consider consulting Legal Aid before reporting"
            ]
        }
        
        if fraud_type:
            fraud_key = fraud_type.lower()
            if "hud" in fraud_key or "section" in fraud_key:
                protections["recommended_agency"] = "HUD Office of Inspector General"
            elif "discrimination" in fraud_key:
                protections["recommended_agency"] = "HUD FHEO or MN Dept of Human Rights"
            else:
                protections["recommended_agency"] = "MN Attorney General Consumer Division"
        
        return protections

    def get_all_patterns(self) -> List[Dict[str, Any]]:
        """Get all fraud detection patterns/rules"""
        patterns = []
        for rule_name, rule_data in FRAUD_RULES.items():
            patterns.append({
                "id": rule_name,
                "fraud_type": rule_data["fraud_type"].value,
                "severity": rule_data["severity"].value,
                "description": rule_data["description"],
                "reporting_agencies": rule_data["reporting_agencies"]
            })
        return patterns

    def get_reporting_agencies(self) -> List[Dict[str, Any]]:
        """Get list of agencies for reporting fraud"""
        return [
            {
                "id": "hud_oig",
                "name": "HUD Office of Inspector General",
                "jurisdiction": "federal",
                "fraud_types": ["subsidy_fraud", "section_8", "fha"],
                "hotline": "1-800-347-3735",
                "website": "https://www.hudoig.gov/hotline",
                "online_form": True
            },
            {
                "id": "mn_ag",
                "name": "Minnesota Attorney General",
                "jurisdiction": "state",
                "fraud_types": ["consumer_fraud", "habitability", "illegal_fees"],
                "hotline": "(651) 296-3353",
                "website": "https://www.ag.state.mn.us/consumer/",
                "online_form": True
            },
            {
                "id": "hud_fheo",
                "name": "HUD Fair Housing & Equal Opportunity",
                "jurisdiction": "federal",
                "fraud_types": ["discrimination", "fair_housing"],
                "hotline": "1-800-669-9777",
                "website": "https://www.hud.gov/fairhousing",
                "online_form": True
            },
            {
                "id": "mn_human_rights",
                "name": "Minnesota Department of Human Rights",
                "jurisdiction": "state",
                "fraud_types": ["discrimination", "fair_housing"],
                "hotline": "(651) 539-1100",
                "website": "https://mn.gov/mdhr/",
                "online_form": True
            },
            {
                "id": "cfpb",
                "name": "Consumer Financial Protection Bureau",
                "jurisdiction": "federal",
                "fraud_types": ["mortgage_fraud", "lending"],
                "hotline": "(855) 411-2372",
                "website": "https://www.consumerfinance.gov/",
                "online_form": True
            },
            {
                "id": "local_housing",
                "name": "Local Housing Authority",
                "jurisdiction": "local",
                "fraud_types": ["section_8", "subsidy_fraud"],
                "notes": "Contact your local PHA for Section 8 issues"
            },
            {
                "id": "city_inspector",
                "name": "City Housing Inspector",
                "jurisdiction": "local",
                "fraud_types": ["habitability", "code_violations"],
                "notes": "Contact your city's housing inspection department"
            }
        ]


# Global instance
_fraud_service: Optional[FraudExposureService] = None


def get_fraud_service() -> FraudExposureService:
    """Get the fraud exposure service singleton"""
    global _fraud_service
    if _fraud_service is None:
        _fraud_service = FraudExposureService()
    return _fraud_service
