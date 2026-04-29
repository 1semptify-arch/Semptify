"""
Public Exposure Module - Press Release & Media Campaign Generation
==================================================================

Generates professional press releases and media kits for:
- Tenant rights violations
- Landlord misconduct exposure
- Community organizing campaigns
- Media outreach coordination
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ReleaseType(str, Enum):
    """Types of press releases"""
    VIOLATION_EXPOSURE = "violation_exposure"
    COMMUNITY_ACTION = "community_action"
    LEGAL_UPDATE = "legal_update"
    SETTLEMENT_ANNOUNCEMENT = "settlement_announcement"
    POLICY_ADVOCACY = "policy_advocacy"


class MediaOutlet(str, Enum):
    """Target media outlets"""
    LOCAL_NEWS = "local_news"
    INVESTIGATIVE = "investigative"
    COMMUNITY_PAPER = "community_paper"
    RADIO = "radio"
    ONLINE = "online"
    SOCIAL_MEDIA = "social_media"


@dataclass
class PressRelease:
    """Generated press release"""
    id: str
    headline: str
    subheadline: Optional[str]
    lede: str  # Opening paragraph
    body: List[str]  # Body paragraphs
    quotes: List[Dict[str, str]]  # {"speaker": "name", "quote": "text"}
    call_to_action: str
    boilerplate: str  # About section
    contact_info: Dict[str, str]
    bundle_link: Optional[str]
    created_at: datetime
    language: str = "en"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "headline": self.headline,
            "subheadline": self.subheadline,
            "lede": self.lede,
            "body": self.body,
            "quotes": self.quotes,
            "call_to_action": self.call_to_action,
            "boilerplate": self.boilerplate,
            "contact_info": self.contact_info,
            "bundle_link": self.bundle_link,
            "created_at": self.created_at.isoformat(),
            "language": self.language,
        }
    
    def to_text(self) -> str:
        """Convert to formatted text"""
        lines = [
            "FOR IMMEDIATE RELEASE",
            "",
            self.headline.upper(),
            self.subheadline or "",
            "",
            self.lede,
            "",
        ]
        
        for para in self.body:
            lines.extend([para, ""])
        
        for quote in self.quotes:
            lines.extend([
                f'"{quote["quote"]}"',
                f'— {quote["speaker"]}',
                "",
            ])
        
        lines.extend([
            "###",
            "",
            self.call_to_action,
            "",
            "ABOUT:",
            self.boilerplate,
            "",
            "MEDIA CONTACT:",
        ])
        
        for key, value in self.contact_info.items():
            lines.append(f"{key}: {value}")
        
        if self.bundle_link:
            lines.extend(["", f"Evidence Bundle: {self.bundle_link}"])
        
        return "\n".join(lines)


@dataclass 
class MediaKit:
    """Complete media kit for campaign"""
    id: str
    press_release: PressRelease
    fact_sheet: Dict[str, Any]
    timeline: List[Dict[str, str]]
    evidence_summary: List[str]
    suggested_angles: List[str]
    media_targets: List[Dict[str, str]]
    social_media_posts: List[Dict[str, str]]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "press_release": self.press_release.to_dict(),
            "fact_sheet": self.fact_sheet,
            "timeline": self.timeline,
            "evidence_summary": self.evidence_summary,
            "suggested_angles": self.suggested_angles,
            "media_targets": self.media_targets,
            "social_media_posts": self.social_media_posts,
            "created_at": self.created_at.isoformat(),
        }


# Templates for different languages
TEMPLATES = {
    "en": {
        "boilerplate": "Semptify is a tenant rights technology platform helping renters understand their legal rights, organize evidence, and hold landlords accountable. Learn more at semptify.org",
        "cta_template": "For more information or to schedule an interview, contact {contact}.",
    },
    "es": {
        "boilerplate": "Semptify es una plataforma tecnológica de derechos de inquilinos que ayuda a los inquilinos a comprender sus derechos legales, organizar pruebas y responsabilizar a los propietarios.",
        "cta_template": "Para más información o para programar una entrevista, contacte a {contact}.",
    },
    "hmn": {
        "boilerplate": "Semptify yog ib lub platform technology txog cov neeg xauj tsev txoj cai pab cov neeg xauj tsev nkag siab lawv txoj cai raug cai, npaj pov thawj, thiab tuav cov tswv tsev lub luag haujlwm.",
        "cta_template": "Yog xav paub ntxiv los yog teem sijhawm xam phaj, hu rau {contact}.",
    },
    "so": {
        "boilerplate": "Semptify waa goob tignoolajiyeed oo ku saabsan xuquuqda kireystayaasha oo ka caawisa kireystayaasha inay fahmaan xuquuqdooda sharciga ah.",
        "cta_template": "Wixii macluumaad dheeraad ah ama si aad u qabato wareysiga, la xiriir {contact}.",
    },
}


# Minnesota media outlets database
MN_MEDIA_OUTLETS = [
    {"name": "Star Tribune", "type": MediaOutlet.LOCAL_NEWS, "beat": "housing", "email": "tips@startribune.com"},
    {"name": "MPR News", "type": MediaOutlet.RADIO, "beat": "housing", "email": "news@mpr.org"},
    {"name": "KARE 11", "type": MediaOutlet.LOCAL_NEWS, "beat": "investigative", "email": "investigators@kare11.com"},
    {"name": "WCCO", "type": MediaOutlet.LOCAL_NEWS, "beat": "consumer", "email": "tips@wcco.com"},
    {"name": "Southwest Journal", "type": MediaOutlet.COMMUNITY_PAPER, "beat": "local", "email": "editor@swjournal.com"},
    {"name": "Sahan Journal", "type": MediaOutlet.COMMUNITY_PAPER, "beat": "immigrant_communities", "email": "tips@sahanjournal.com"},
    {"name": "Minnesota Reformer", "type": MediaOutlet.INVESTIGATIVE, "beat": "housing_policy", "email": "tips@minnesotareformer.com"},
]


class PublicExposureService:
    """Service for generating press releases and media campaigns"""
    
    def __init__(self):
        self._releases: Dict[str, PressRelease] = {}
        self._kits: Dict[str, MediaKit] = {}
        logger.info("📰 Public Exposure Service initialized")
    
    async def generate_press_release(
        self,
        property_address: str,
        violations: List[str],
        contact_info: Dict[str, str],
        bundle_link: Optional[str] = None,
        language: str = "en",
        landlord_name: Optional[str] = None,
        tenant_count: Optional[int] = None,
        fraud_findings: Optional[List[Dict[str, Any]]] = None,
        quotes: Optional[List[Dict[str, str]]] = None,
    ) -> PressRelease:
        """
        Generate a press release for tenant rights violations.
        
        Args:
            property_address: Property address
            violations: List of violation descriptions
            contact_info: Contact information dict
            bundle_link: Link to evidence bundle
            language: Language code (en, es, hmn, so)
            landlord_name: Landlord/company name
            tenant_count: Number of affected tenants
            fraud_findings: Fraud analysis findings
            quotes: Spokesperson quotes
            
        Returns:
            PressRelease object
        """
        template = TEMPLATES.get(language, TEMPLATES["en"])
        
        # Generate headline
        if landlord_name:
            headline = f"Tenants Expose Housing Violations at {landlord_name} Property"
        else:
            headline = f"Tenants Expose Housing Violations at {property_address}"
        
        # Generate subheadline
        subheadline = None
        if len(violations) > 0:
            subheadline = f"{len(violations)} documented violations prompt regulatory complaints"
        
        # Generate lede
        tenant_phrase = f"{tenant_count} tenants" if tenant_count else "Tenants"
        violation_summary = violations[0] if violations else "multiple housing code violations"
        lede = f"{tenant_phrase} at {property_address} are speaking out about {violation_summary} and other issues that have gone unaddressed despite repeated complaints to management."
        
        # Generate body paragraphs
        body = []
        
        # Violations paragraph
        if violations:
            body.append(f"The documented issues include: {'; '.join(violations)}.")
        
        # Fraud findings paragraph
        if fraud_findings:
            high_severity = [f for f in fraud_findings if f.get("severity") in ["high", "critical"]]
            if high_severity:
                body.append(f"An analysis of the case has revealed {len(high_severity)} serious findings that may constitute fraud, including potential violations of federal housing programs.")
        
        # Impact paragraph
        if tenant_count:
            body.append(f"The issues affect approximately {tenant_count} residents who have been paying rent while living with substandard conditions.")
        
        # Action paragraph
        body.append("Tenants have filed complaints with relevant regulatory agencies and are calling for immediate action to address the violations.")
        
        # Default quotes if none provided
        if not quotes:
            quotes = [
                {
                    "speaker": "Affected Tenant",
                    "quote": "We've tried to work with management, but nothing changes. We're speaking out because tenants deserve safe housing."
                }
            ]
        
        # Generate CTA
        contact_name = contact_info.get("name", contact_info.get("email", "the contact below"))
        cta = template["cta_template"].format(contact=contact_name)
        
        # Create release
        release_id = f"pr_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        release = PressRelease(
            id=release_id,
            headline=headline,
            subheadline=subheadline,
            lede=lede,
            body=body,
            quotes=quotes,
            call_to_action=cta,
            boilerplate=template["boilerplate"],
            contact_info=contact_info,
            bundle_link=bundle_link,
            created_at=datetime.now(timezone.utc),
            language=language,
        )
        
        self._releases[release_id] = release
        logger.info(f"📰 Press release generated: {release_id}")
        
        return release
    
    async def generate_media_kit(
        self,
        press_release: PressRelease,
        timeline_events: List[Dict[str, str]],
        evidence_docs: List[str],
        target_outlets: Optional[List[str]] = None,
    ) -> MediaKit:
        """
        Generate a complete media kit for a campaign.
        
        Args:
            press_release: The press release
            timeline_events: List of {"date": "...", "event": "..."} 
            evidence_docs: List of evidence document descriptions
            target_outlets: Optional list of target outlet names
            
        Returns:
            MediaKit object
        """
        # Generate fact sheet
        fact_sheet = {
            "property": press_release.contact_info.get("property", "Unknown"),
            "violations_count": len(press_release.body),
            "key_issues": press_release.body,
            "contact": press_release.contact_info,
        }
        
        # Suggested story angles
        suggested_angles = [
            "Tenant organizing in action: How renters are holding landlords accountable",
            "The hidden housing crisis: Violations going unchecked in rental properties",
            "Regulatory gaps: Why some landlords face no consequences",
            "Technology and tenant rights: New tools for documenting violations",
        ]
        
        # Get relevant media targets
        if target_outlets:
            media_targets = [m for m in MN_MEDIA_OUTLETS if m["name"] in target_outlets]
        else:
            # Default to all outlets
            media_targets = MN_MEDIA_OUTLETS
        
        # Generate social media posts
        social_posts = [
            {
                "platform": "Twitter/X",
                "post": f"🏠 THREAD: Tenants at {press_release.contact_info.get('property', 'a local property')} are exposing housing violations. Here's what we found... #TenantRights #HousingJustice",
            },
            {
                "platform": "Facebook",
                "post": f"Tenants are speaking out about housing violations that have gone unaddressed. Read the full story and support tenant rights. {press_release.bundle_link or ''}",
            },
            {
                "platform": "Instagram",
                "post": f"🏠 Housing violations exposed\n\nTenants deserve safe homes. When landlords don't maintain properties, tenants organize.\n\n#TenantRights #HousingJustice #RentersRights",
            },
        ]
        
        # Create kit
        kit_id = f"mk_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        kit = MediaKit(
            id=kit_id,
            press_release=press_release,
            fact_sheet=fact_sheet,
            timeline=timeline_events,
            evidence_summary=evidence_docs,
            suggested_angles=suggested_angles,
            media_targets=media_targets,
            social_media_posts=social_posts,
            created_at=datetime.now(timezone.utc),
        )
        
        self._kits[kit_id] = kit
        logger.info(f"📰 Media kit generated: {kit_id}")
        
        return kit
    
    def get_press_release(self, release_id: str) -> Optional[PressRelease]:
        """Get a press release by ID"""
        return self._releases.get(release_id)
    
    def get_media_kit(self, kit_id: str) -> Optional[MediaKit]:
        """Get a media kit by ID"""
        return self._kits.get(kit_id)
    
    def get_mn_media_outlets(self, outlet_type: Optional[MediaOutlet] = None) -> List[Dict[str, str]]:
        """Get Minnesota media outlets, optionally filtered by type"""
        if outlet_type:
            return [m for m in MN_MEDIA_OUTLETS if m["type"] == outlet_type]
        return MN_MEDIA_OUTLETS


# Global instance
_public_service: Optional[PublicExposureService] = None


def get_public_exposure_service() -> PublicExposureService:
    """Get the public exposure service singleton"""
    global _public_service
    if _public_service is None:
        _public_service = PublicExposureService()
    return _public_service
