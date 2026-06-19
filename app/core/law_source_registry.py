"""
Law Source Registry — Single Source of Truth for official law URLs.

Maps every citation type to its official source URL builder + verification metadata.
All law cards, modals, and the law-linker JS use this to provide clickable
direct links to the authoritative source.

Citation types covered:
  - Minnesota Statutes (revisor.mn.gov)
  - US Code (law.cornell.edu + govinfo.gov fallback)
  - Code of Federal Regulations (ecfr.gov)
  - IRS Publications (irs.gov)
  - Minnesota Rules (mn.gov/revisor)
  - Minneapolis Code of Ordinances (library.municode.com)
  - St. Paul Legislative Code (library.municode.com)
  - Hennepin County Ordinances (hennepin.us)
  - US Supreme Court cases (courtlistener.com + supremecourt.gov)
  - Federal appellate cases (courtlistener.com)
  - Minnesota case law (mn.gov)
  - HUD regulations (hud.gov)
  - ADA.gov (ada.gov)

TODO (post-funding): Build a live-feed verification engine that continuously
checks all registered URLs and alerts when a source page moves or a statute
is amended. For now, last_verified dates are manually maintained and displayed
on every card so users know the freshness of each link.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LawSource:
    """A single official source mapping."""
    source_name: str
    url_builder: Callable[[str], str]
    last_verified: str
    jurisdiction: str  # "federal", "state", "local"
    notes: Optional[str] = None


def _mn_stat_url(citation: str) -> str:
    """Build revisor.mn.gov URL from Minn. Stat. citation."""
    # Extract the chapter.section, e.g. "504B.321" from "Minn. Stat. § 504B.321" or "Minn. Stat. Sec. 504B.321"
    m = re.search(r"(\d+[A-Z]?\.\d+[\w.]*)", citation)
    if m:
        return f"https://www.revisor.mn.gov/statutes/cite/{m.group(1)}"
    return "https://www.revisor.mn.gov/statutes/"


def _mn_stat_chapter_url(citation: str) -> str:
    """Build revisor.mn.gov URL for chapter-level citations (e.g. § 504B, § 580, Sec. 504)."""
    # Strip any "Sec." or "Section" prefix, then look for chapter number
    cleaned = re.sub(r"(?i)\bSec\.?\s*|\bSection\s*", "", citation)
    m = re.search(r"(\d+[A-Z]?)", cleaned)
    if m:
        return f"https://www.revisor.mn.gov/statutes/cite/{m.group(1)}"
    return "https://www.revisor.mn.gov/statutes/"


def _usc_url(citation: str) -> str:
    """Build Cornell LII URL for U.S. Code citations."""
    # e.g. "42 U.S.C. § 3601-3619" -> 42/3601
    m = re.search(r"(\d+)\s*U\.?S\.?C\.?\s*[§\s]*(\d+)", citation)
    if m:
        title, section = m.group(1), m.group(2)
        return f"https://www.law.cornell.edu/uscode/text/{title}/{section}"
    return "https://www.law.cornell.edu/uscode/text"


def _cfr_url(citation: str) -> str:
    """Build eCFR URL for Code of Federal Regulations citations."""
    # e.g. "24 C.F.R. § 100.204" -> title 24, section 100.204
    m = re.search(r"(\d+)\s*C\.?F\.?R\.?\s*[§\s]*([\d.]+)", citation)
    if m:
        title, section = m.group(1), m.group(2)
        return f"https://www.ecfr.gov/current/title-{title}/section-{section}"
    return "https://www.ecfr.gov/"


def _irs_pub_url(citation: str) -> str:
    """Build IRS.gov URL for IRS Publication citations."""
    # e.g. "IRS Publication 527" -> irs.gov/publications/p527
    m = re.search(r"Publication\s*(\d+)", citation, re.IGNORECASE)
    if m:
        return f"https://www.irs.gov/publications/p{m.group(1)}"
    return "https://www.irs.gov/publications"


def _minneapolis_code_url(citation: str) -> str:
    """Build Municode URL for Minneapolis Code citations."""
    # e.g. "Minneapolis Code § 244" -> library.municode.com/mn/minneapolis
    return "https://library.municode.com/mn/minneapolis"


def _stpaul_code_url(citation: str) -> str:
    """Build Municode URL for St. Paul Code citations."""
    return "https://library.municode.com/mn/st-paul"


def _hennepin_url(citation: str) -> str:
    """Build Hennepin County URL."""
    return "https://www.hennepin.us/property-tax"


def _scotus_url(citation: str) -> str:
    """Build CourtListener URL for US Supreme Court citations."""
    # e.g. "576 U.S. 519 (2015)" -> courtlistener.com
    m = re.search(r"(\d+)\s*U\.?S\.?\s*(\d+)", citation)
    if m:
        return f"https://www.courtlistener.com/?q=%22{m.group(0)}%22&type=o"
    return "https://www.supremecourt.gov/opinions/opinions.html"


def _federal_appellate_url(citation: str) -> str:
    """Build CourtListener URL for federal appellate citations."""
    # e.g. "343 F.3d 1143 (9th Cir. 2003)"
    return f"https://www.courtlistener.com/?q=%22{citation}%22&type=o"


def _mn_case_url(citation: str) -> str:
    """Build Minnesota case law URL."""
    # e.g. "298 Minn. 54, 213 N.W.2d 339 (1973)"
    return f"https://www.courtlistener.com/?q=%22{citation}%22&type=o"


def _hud_url(citation: str) -> str:
    """Build HUD.gov URL for HUD-related citations."""
    return "https://www.hud.gov/program_offices/fair_housing_equal_opp"


def _ada_url(citation: str) -> str:
    """Build ADA.gov URL for ADA-related citations."""
    return "https://ada.gov/housing-and-housing-related/"


# =============================================================================
# Registry — maps citation patterns to LawSource objects
# =============================================================================

REGISTRY: list[tuple[re.Pattern, LawSource]] = [
    # Minnesota Statutes — section level (e.g. § 504B.321, Sec. 504B.321, Section 504B.321)
    (re.compile(r"Minn\.?\s*Stat\.?\s*(?:§|Sec\.?|Section)?\s*\d+[A-Z]?\.\d+", re.IGNORECASE),
     LawSource("Minnesota Revisor of Statutes", _mn_stat_url, "2026-01-15", "state")),
    # Minnesota Statutes — chapter level (e.g. § 504B, Sec. 504, Section 580)
    (re.compile(r"Minn\.?\s*Stat\.?\s*(?:§|Sec\.?|Section)?\s*\d+[A-Z]?(?:\s|$)", re.IGNORECASE),
     LawSource("Minnesota Revisor of Statutes", _mn_stat_chapter_url, "2026-01-15", "state")),
    # US Code
    (re.compile(r"\d+\s*U\.?S\.?C\.?", re.IGNORECASE),
     LawSource("Cornell LII (U.S. Code)", _usc_url, "2026-01-15", "federal")),
    # Code of Federal Regulations
    (re.compile(r"\d+\s*C\.?F\.?R\.?", re.IGNORECASE),
     LawSource("eCFR (Electronic CFR)", _cfr_url, "2026-01-15", "federal")),
    # IRS Publications
    (re.compile(r"IRS\s*Publication\s*\d+", re.IGNORECASE),
     LawSource("IRS.gov", _irs_pub_url, "2026-01-15", "federal")),
    # Minneapolis Code
    (re.compile(r"Minneapolis\s*(?:Code|Ordinance)", re.IGNORECASE),
     LawSource("Minneapolis Municode", _minneapolis_code_url, "2026-01-15", "local")),
    # St. Paul Code
    (re.compile(r"St\.?\s*Paul\s*(?:Code|Ordinance|Legislative)", re.IGNORECASE),
     LawSource("St. Paul Municode", _stpaul_code_url, "2026-01-15", "local")),
    # Hennepin County
    (re.compile(r"Hennepin\s*County", re.IGNORECASE),
     LawSource("Hennepin County", _hennepin_url, "2026-01-15", "local")),
    # US Supreme Court
    (re.compile(r"\d+\s*U\.?S\.?\s*\d+\s*\(\d{4}\)", re.IGNORECASE),
     LawSource("CourtListener (SCOTUS)", _scotus_url, "2026-01-15", "federal")),
    # Federal appellate
    (re.compile(r"\d+\s*F\.\w*\s*\d+\s*\(\w+\s*Cir\.\s*\d{4}\)", re.IGNORECASE),
     LawSource("CourtListener (Federal Appeals)", _federal_appellate_url, "2026-01-15", "federal")),
    # Federal district
    (re.compile(r"\d+\s*F\.\s*Supp\.\s*\w*\s*\d+", re.IGNORECASE),
     LawSource("CourtListener (Federal District)", _federal_appellate_url, "2026-01-15", "federal")),
    # Minnesota case law
    (re.compile(r"\d+\s*Minn\.\s*\d+", re.IGNORECASE),
     LawSource("CourtListener (MN Cases)", _mn_case_url, "2026-01-15", "state")),
    (re.compile(r"\d+\s*N\.?W\.?\w*\s*\d+\s*\(", re.IGNORECASE),
     LawSource("CourtListener (MN Cases)", _mn_case_url, "2026-01-15", "state")),
]


def resolve_source(citation: str) -> Optional[LawSource]:
    """Resolve a citation string to its LawSource, or None if no match."""
    if not citation:
        return None
    for pattern, source in REGISTRY:
        if pattern.search(citation):
            return source
    return None


def build_official_url(citation: str) -> Optional[str]:
    """Build the official URL for a citation, or None if no source matched."""
    source = resolve_source(citation)
    if source is None:
        return None
    try:
        return source.url_builder(citation)
    except Exception as exc:
        logger.warning("URL builder failed for citation %r: %s", citation, exc)
        return None


def enrich_law_entry(entry: dict) -> dict:
    """
    Inject official_url, source_name, last_verified, jurisdiction into a law entry
    based on its citation field. Does not overwrite existing values.
    """
    citation = entry.get("citation", "")
    if not citation:
        return entry
    source = resolve_source(citation)
    if source is None:
        return entry
    if "official_url" not in entry or not entry.get("official_url"):
        entry["official_url"] = build_official_url(citation)
    if "source_name" not in entry or not entry.get("source_name"):
        entry["source_name"] = source.source_name
    if "last_verified" not in entry or not entry.get("last_verified"):
        entry["last_verified"] = source.last_verified
    if "jurisdiction" not in entry or not entry.get("jurisdiction"):
        entry["jurisdiction"] = source.jurisdiction
    return entry
