# app/services/patterns.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..models import Case, Docket, Entity, Attorney
from ..schemas import PatternSummary

# Keywords for pattern detection
DEFAULT_JUDGMENT_KEYWORDS = [
    "default judgment",
    "judgment by default",
    "entry of default",
    "default entered",
    "notice of default",
]

SETTLEMENT_KEYWORDS = [
    "stipulation of dismissal",
    "settlement agreement",
    "dismissal with prejudice",
    "dismissal without prejudice",
    "stipulation",
    "settlement",
    "mutual dismissal",
]

MOTION_KEYWORDS = [
    "motion",
    "motion to",
    "motion for",
]

DISMISSAL_KEYWORDS = [
    "dismissed",
    "dismissal",
    "terminated",
    "closed",
]

async def compute_attorney_patterns(db: AsyncSession, attorney_id: int) -> PatternSummary:
    """
    Compute pattern analysis for an attorney based on their cases and dockets.
    
    Analyzes:
    - Default judgment rate
    - Settlement rate
    - Motion timing (time to first motion)
    - Top opposing entities
    - Court distribution
    """
    # Fetch cases with dockets preloaded
    q = await db.execute(
        select(Case)
        .options(selectinload(Case.dockets), selectinload(Case.entity))
        .where(Case.attorney_id == attorney_id)
    )
    cases = q.scalars().all()

    total = len(cases)
    if total == 0:
        return PatternSummary(
            total_cases=0,
            default_rate=0.0,
            settlement_rate=0.0,
            avg_time_to_first_motion_days=None,
            top_entities=[],
            court_distribution={}
        )

    # Initialize counters
    court_distribution = {}
    entity_counts: Dict[str, int] = {}
    default_count = 0
    settlement_count = 0
    motion_timings: List[int] = []
    
    for c in cases:
        # Count court distribution
        if c.court:
            court_distribution[c.court] = court_distribution.get(c.court, 0) + 1
        
        # Count opposing entities
        if c.entity and c.entity.name:
            entity_counts[c.entity.name] = entity_counts.get(c.entity.name, 0) + 1
        
        # Analyze dockets for patterns
        if c.dockets:
            has_default = False
            has_settlement = False
            first_motion_date = None
            filing_date = c.filing_date
            
            for d in c.dockets:
                description = d.description or ""
                description_lower = description.lower()
                
                # Check for default judgment
                if not has_default:
                    for keyword in DEFAULT_JUDGMENT_KEYWORDS:
                        if keyword in description_lower:
                            has_default = True
                            break
                
                # Check for settlement
                if not has_settlement:
                    for keyword in SETTLEMENT_KEYWORDS:
                        if keyword in description_lower:
                            has_settlement = True
                            break
                
                # Track first motion timing
                if not first_motion_date and d.date:
                    for keyword in MOTION_KEYWORDS:
                        if keyword in description_lower:
                            first_motion_date = d.date
                            break
            
            if has_default:
                default_count += 1
            
            if has_settlement:
                settlement_count += 1
            
            # Calculate time to first motion
            if first_motion_date and filing_date:
                try:
                    if isinstance(filing_date, str):
                        filing_date = datetime.strptime(filing_date, "%Y-%m-%d").date()
                    if isinstance(first_motion_date, str):
                        first_motion_date = datetime.strptime(first_motion_date, "%Y-%m-%d").date()
                    
                    days_to_motion = (first_motion_date - filing_date).days
                    if days_to_motion >= 0:
                        motion_timings.append(days_to_motion)
                except:
                    pass
    
    # Calculate averages
    avg_time_to_motion = None
    if motion_timings:
        avg_time_to_motion = sum(motion_timings) / len(motion_timings)
    
    # Get top entities
    top_entities = sorted(entity_counts, key=entity_counts.get, reverse=True)[:5]
    
    return PatternSummary(
        total_cases=total,
        default_rate=default_count / total if total else 0.0,
        settlement_rate=settlement_count / total if total else 0.0,
        avg_time_to_first_motion_days=avg_time_to_motion,
        top_entities=top_entities,
        court_distribution=court_distribution,
    )

async def compute_entity_patterns(db: AsyncSession, entity_id: int) -> Dict:
    """
    Compute pattern analysis for an entity.
    
    Analyzes:
    - Litigation frequency
    - Shared registered agents
    - Shared addresses
    - Opposing counsel patterns
    """
    q = await db.execute(
        select(Case)
        .options(selectinload(Case.attorney))
        .where(Case.entity_id == entity_id)
    )
    cases = q.scalars().all()
    
    total = len(cases)
    
    # Count attorney appearances
    attorney_counts: Dict[str, int] = {}
    court_distribution = {}
    
    for c in cases:
        if c.attorney and c.attorney.name:
            attorney_counts[c.attorney.name] = attorney_counts.get(c.attorney.name, 0) + 1
        
        if c.court:
            court_distribution[c.court] = court_distribution.get(c.court, 0) + 1
    
    top_attorneys = sorted(attorney_counts, key=attorney_counts.get, reverse=True)[:5]
    
    return {
        "total_cases": total,
        "top_attorneys": top_attorneys,
        "attorney_counts": attorney_counts,
        "court_distribution": court_distribution,
    }

async def detect_shell_llc_clusters(db: AsyncSession) -> List[Dict]:
    """
    Detect potential shell LLC clusters based on shared registered agents and addresses.
    
    Returns clusters of entities that share the same registered agent or address.
    """
    from ..models import Entity, Relationship
    
    # Get all entities
    q = await db.execute(select(Entity))
    entities = q.scalars().all()
    
    # Build clusters by registered agent
    agent_clusters: Dict[str, List[Dict]] = {}
    address_clusters: Dict[str, List[Dict]] = {}
    
    for entity in entities:
        if entity.registered_agent:
            if entity.registered_agent not in agent_clusters:
                agent_clusters[entity.registered_agent] = []
            agent_clusters[entity.registered_agent].append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "sos_id": entity.sos_id,
            })
        
        if entity.address:
            if entity.address not in address_clusters:
                address_clusters[entity.address] = []
            address_clusters[entity.address].append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "sos_id": entity.sos_id,
            })
    
    # Filter for clusters with multiple entities
    significant_agent_clusters = [
        {"agent": agent, "entities": entities}
        for agent, entities in agent_clusters.items()
        if len(entities) > 1
    ]
    
    significant_address_clusters = [
        {"address": address, "entities": entities}
        for address, entities in address_clusters.items()
        if len(entities) > 1
    ]
    
    return {
        "agent_clusters": significant_agent_clusters,
        "address_clusters": significant_address_clusters,
    }
