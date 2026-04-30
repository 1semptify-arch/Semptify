"""
Relationship Mapper
===================

Maps and connects entities found in documents.
Creates a comprehensive relationship graph of:
- Party relationships (tenant-landlord, attorney-client)
- Financial relationships (who owes what to whom)
- Temporal relationships (sequence of events)
- Property relationships (who lives where)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict

from .models import (
    ExtractedEntity, EntityType, PartyRole,
    RelationshipMap, PartyRelationship, AmountRelationship,
    TimelineEntry, ReasoningChain, ReasoningStep, ReasoningType,
)


@dataclass
class RelationshipCandidate:
    """A candidate relationship to be validated"""
    entity_a_id: str
    entity_b_id: str
    relationship_type: str
    confidence: float
    evidence: str


class RelationshipMapper:
    """
    Maps relationships between extracted entities.
    
    Capabilities:
    - Identify party roles and relationships
    - Connect financial amounts to parties
    - Build timeline from events
    - Map property/address relationships
    - Detect legal entity connections
    """
    
    def __init__(self):
        self.role_indicators = self._build_role_indicators()
        self.relationship_patterns = self._build_relationship_patterns()
        self.amount_contexts = self._build_amount_contexts()
        
    def _build_role_indicators(self) -> Dict[PartyRole, List[str]]:
        """Build patterns for inferring party roles"""
        return {
            PartyRole.TENANT: [
                "tenant", "lessee", "renter", "occupant", "resident",
                "defendant", "respondent",
            ],
            PartyRole.LANDLORD: [
                "landlord", "lessor", "owner", "property owner",
                "plaintiff", "petitioner",
            ],
            PartyRole.PROPERTY_MANAGER: [
                "property manager", "manager", "management company",
                "property management", "on behalf of",
            ],
            PartyRole.MANAGEMENT_COMPANY: [
                "management llc", "management inc", "management company",
                "properties llc", "realty", "real estate",
            ],
            PartyRole.ATTORNEY: [
                "attorney", "lawyer", "counsel", "esq", "law firm",
                "attorney for", "representing",
            ],
            PartyRole.JUDGE: [
                "judge", "honorable", "the court", "presiding",
            ],
            PartyRole.PROCESS_SERVER: [
                "process server", "served by", "service of process",
            ],
            PartyRole.HOUSING_AUTHORITY: [
                "housing authority", "pha", "hud", "section 8",
                "public housing",
            ],
        }
    
    def _build_relationship_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build patterns for identifying relationships"""
        return {
            "landlord_tenant": {
                "indicators": [
                    r"(?:tenant|lessee).*(?:landlord|lessor|owner)",
                    r"(?:landlord|lessor|owner).*(?:tenant|lessee)",
                    r"(?:lease|rental)\s+agreement\s+between",
                ],
                "roles": [PartyRole.LANDLORD, PartyRole.TENANT],
            },
            "attorney_client": {
                "indicators": [
                    r"(?:attorney|counsel)\s+for\s+(?:plaintiff|defendant)",
                    r"representing\s+(?:plaintiff|defendant)",
                ],
                "roles": [PartyRole.ATTORNEY],
            },
            "manager_owner": {
                "indicators": [
                    r"(?:on\s+behalf\s+of|acting\s+for|agent\s+of)",
                    r"(?:property\s+manager|managing\s+agent)",
                ],
                "roles": [PartyRole.PROPERTY_MANAGER, PartyRole.LANDLORD],
            },
            "vs_relationship": {
                "indicators": [
                    r"(\w+)\s+(?:v\.?|vs\.?|versus)\s+(\w+)",
                ],
                "roles": [PartyRole.LANDLORD, PartyRole.TENANT],  # Typically plaintiff/defendant
            },
        }
    
    def _build_amount_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Build context patterns for financial amounts"""
        return {
            "rent_owed": {
                "patterns": [
                    r"rent\s+(?:owed|due|owing|in\s+arrears)",
                    r"(?:past\s+due|delinquent)\s+rent",
                    r"unpaid\s+rent",
                ],
                "period": "monthly",
            },
            "security_deposit": {
                "patterns": [
                    r"security\s+deposit",
                    r"damage\s+deposit",
                    r"pet\s+deposit",
                ],
                "period": "one-time",
            },
            "late_fee": {
                "patterns": [
                    r"late\s+(?:fee|charge|penalty)",
                    r"(?:fee|charge)\s+for\s+late\s+(?:payment|rent)",
                ],
                "period": "per-occurrence",
            },
            "monthly_rent": {
                "patterns": [
                    r"monthly\s+rent",
                    r"rent\s+(?:is|of|:)\s*\$",
                    r"per\s+month",
                ],
                "period": "monthly",
            },
            "damages": {
                "patterns": [
                    r"(?:damage|damages)\s+(?:to|for)",
                    r"repair\s+(?:cost|charge)",
                    r"cleaning\s+(?:fee|charge)",
                ],
                "period": "one-time",
            },
            "court_costs": {
                "patterns": [
                    r"(?:court|filing)\s+(?:cost|fee)",
                    r"(?:cost|fee)\s+of\s+(?:court|filing)",
                ],
                "period": "one-time",
            },
            "attorney_fees": {
                "patterns": [
                    r"attorney(?:'s)?\s+fee",
                    r"legal\s+(?:fee|cost)",
                ],
                "period": "one-time",
            },
            "total_owed": {
                "patterns": [
                    r"total\s+(?:amount|owed|due|balance)",
                    r"(?:sum|balance)\s+(?:of|due)",
                ],
                "period": "total",
            },
        }
    
    async def map_relationships(self, text: str, 
                                entities: List[ExtractedEntity],
                                timeline: List[TimelineEntry]) -> Tuple[
        RelationshipMap, ReasoningChain
    ]:
        """
        Build complete relationship map from entities.
        
        Returns:
            Tuple of (RelationshipMap, ReasoningChain)
        """
        reasoning = ReasoningChain(pass_number=1)
        reasoning.add_step(
            ReasoningType.ENTITY_RELATIONSHIP,
            "Beginning relationship mapping",
            {"entity_count": len(entities)},
            {}
        )
        
        rel_map = RelationshipMap()
        
        # Step 1: Categorize entities
        rel_map.parties = [e for e in entities if e.entity_type == EntityType.PERSON]
        rel_map.amounts = [e for e in entities if e.entity_type == EntityType.MONEY]
        rel_map.dates = [e for e in entities if e.entity_type == EntityType.DATE]
        rel_map.addresses = [e for e in entities if e.entity_type == EntityType.ADDRESS]
        rel_map.statutes_cited = [e for e in entities if e.entity_type == EntityType.STATUTE]
        rel_map.case_numbers = [e for e in entities if e.entity_type == EntityType.COURT_CASE]
        
        # Step 2: Infer and assign party roles
        self._assign_party_roles(rel_map.parties, text, reasoning)
        
        # Step 3: Build party relationships
        rel_map.party_relationships = self._build_party_relationships(
            rel_map.parties, text, reasoning
        )
        
        # Step 4: Build amount relationships
        rel_map.amount_relationships = self._build_amount_relationships(
            rel_map.amounts, rel_map.parties, text, reasoning
        )
        
        # Step 5: Identify primary property
        rel_map.primary_property = self._identify_primary_property(
            rel_map.addresses, text, reasoning
        )
        
        # Step 6: Build timeline
        rel_map.timeline = self._enhance_timeline(timeline, entities, reasoning)
        
        # Step 7: Link entities based on proximity
        self._link_by_proximity(entities, text, reasoning)
        
        reasoning.completed_at = datetime.now()
        reasoning.conclusion = (
            f"Mapped {len(rel_map.party_relationships)} party relationships, "
            f"{len(rel_map.amount_relationships)} financial relationships"
        )
        
        return rel_map, reasoning
    
    def _assign_party_roles(self, parties: List[ExtractedEntity], 
                            text: str, reasoning: ReasoningChain):
        """Assign roles to party entities"""
        text_lower = text.lower()
        
        for party in parties:
            if party.attributes.get("role"):
                continue  # Already assigned
            
            party_lower = party.value.lower()
            
            # Find context around the party name
            pos = text_lower.find(party_lower)
            if pos == -1:
                continue
            
            context_start = max(0, pos - 100)
            context_end = min(len(text), pos + len(party.value) + 100)
            context = text_lower[context_start:context_end]
            
            # Check each role's indicators
            best_role = PartyRole.UNKNOWN
            best_score = 0
            
            for role, indicators in self.role_indicators.items():
                score = sum(1 for ind in indicators if ind in context)
                if score > best_score:
                    best_score = score
                    best_role = role
            
            party.attributes["role"] = best_role.value
            party.attributes["role_confidence"] = min(0.95, 0.5 + best_score * 0.15)
        
        # Use document position hints
        # First party mentioned is often the plaintiff/landlord
        if parties and not parties[0].attributes.get("role"):
            if "v." in text or "vs." in text:
                parties[0].attributes["role"] = PartyRole.LANDLORD.value
                parties[0].attributes["role_confidence"] = 0.7
        
        reasoning.add_step(
            ReasoningType.ENTITY_RELATIONSHIP,
            f"Assigned roles to {len(parties)} parties",
            {},
            {
                "role_distribution": self._count_roles(parties)
            },
            confidence_impact=5
        )
    
    def _count_roles(self, parties: List[ExtractedEntity]) -> Dict[str, int]:
        """Count party roles"""
        counts = defaultdict(int)
        for party in parties:
            role = party.attributes.get("role", PartyRole.UNKNOWN.value)
            counts[role] += 1
        return dict(counts)
    
    def _build_party_relationships(self, parties: List[ExtractedEntity],
                                    text: str,
                                    reasoning: ReasoningChain) -> List[PartyRelationship]:
        """Build relationships between parties"""
        relationships = []
        text_lower = text.lower()
        
        # Find tenant-landlord relationship
        tenants = [p for p in parties if p.attributes.get("role") == PartyRole.TENANT.value]
        landlords = [p for p in parties if p.attributes.get("role") in 
                    [PartyRole.LANDLORD.value, PartyRole.PROPERTY_MANAGER.value]]
        
        for tenant in tenants:
            for landlord in landlords:
                relationship = PartyRelationship(
                    party_a_id=landlord.id,
                    party_a_role=PartyRole.LANDLORD,
                    party_a_name=landlord.value,
                    party_b_id=tenant.id,
                    party_b_role=PartyRole.TENANT,
                    party_b_name=tenant.value,
                    relationship_type="landlord_tenant",
                    confidence=0.85,
                )
                relationships.append(relationship)
        
        # Find vs. relationships (court cases)
        vs_match = re.search(
            r"([A-Z][A-Za-z\s]+?)\s+(?:v\.?|vs\.?|versus)\s+([A-Z][A-Za-z\s]+)",
            text
        )
        if vs_match:
            plaintiff_name = vs_match.group(1).strip()
            defendant_name = vs_match.group(2).strip()
            
            # Find matching entities
            plaintiff = next((p for p in parties if plaintiff_name.lower() in p.value.lower()), None)
            defendant = next((p for p in parties if defendant_name.lower() in p.value.lower()), None)
            
            if plaintiff and defendant:
                relationship = PartyRelationship(
                    party_a_id=plaintiff.id,
                    party_a_role=PartyRole.LANDLORD,  # Typically in eviction cases
                    party_a_name=plaintiff.value,
                    party_b_id=defendant.id,
                    party_b_role=PartyRole.TENANT,
                    party_b_name=defendant.value,
                    relationship_type="legal_adversary",
                    confidence=0.9,
                )
                relationships.append(relationship)
        
        # Find attorney relationships
        attorneys = [p for p in parties if p.attributes.get("role") == PartyRole.ATTORNEY.value]
        for attorney in attorneys:
            # Find who they represent
            pos = text_lower.find(attorney.value.lower())
            if pos != -1:
                context = text_lower[max(0, pos-50):pos+len(attorney.value)+50]
                
                if "plaintiff" in context or "landlord" in context:
                    for landlord in landlords:
                        rel = PartyRelationship(
                            party_a_id=attorney.id,
                            party_a_role=PartyRole.ATTORNEY,
                            party_a_name=attorney.value,
                            party_b_id=landlord.id,
                            party_b_role=PartyRole.LANDLORD,
                            party_b_name=landlord.value,
                            relationship_type="attorney_client",
                            confidence=0.8,
                        )
                        relationships.append(rel)
                elif "defendant" in context or "tenant" in context:
                    for tenant in tenants:
                        rel = PartyRelationship(
                            party_a_id=attorney.id,
                            party_a_role=PartyRole.ATTORNEY,
                            party_a_name=attorney.value,
                            party_b_id=tenant.id,
                            party_b_role=PartyRole.TENANT,
                            party_b_name=tenant.value,
                            relationship_type="attorney_client",
                            confidence=0.8,
                        )
                        relationships.append(rel)
        
        reasoning.add_step(
            ReasoningType.ENTITY_RELATIONSHIP,
            f"Built {len(relationships)} party relationships",
            {},
            {
                "types": list(set(r.relationship_type for r in relationships))
            }
        )
        
        return relationships
    
    def _build_amount_relationships(self, amounts: List[ExtractedEntity],
                                    parties: List[ExtractedEntity],
                                    text: str,
                                    reasoning: ReasoningChain) -> List[AmountRelationship]:
        """Build relationships for financial amounts"""
        relationships = []
        text_lower = text.lower()
        
        # Get tenant and landlord
        tenant = next(
            (p for p in parties if p.attributes.get("role") == PartyRole.TENANT.value),
            None
        )
        landlord = next(
            (p for p in parties if p.attributes.get("role") in 
             [PartyRole.LANDLORD.value, PartyRole.PROPERTY_MANAGER.value]),
            None
        )
        
        for amount in amounts:
            # Parse amount value
            try:
                value_str = amount.value.replace(",", "").replace("$", "")
                amount_value = float(value_str)
            except ValueError:
                continue
            
            # Find amount type from context
            amount_type = amount.attributes.get("amount_type", "unknown")
            if amount_type == "unknown":
                amount_type = self._infer_amount_type(amount, text)
            
            # Determine period
            period = self._get_period_for_type(amount_type)
            
            # Check for illegal late fee
            may_be_illegal = False
            illegality_reason = None
            
            if amount_type == "late_fee":
                if amount_value > 100:  # Rough heuristic for excessive fee
                    may_be_illegal = True
                    illegality_reason = "Late fee may be excessive under Minnesota law"
            
            # Check for disputed amount
            is_disputed = False
            dispute_reason = None
            
            pos = amount.start_position
            context = text_lower[max(0, pos-100):min(len(text), pos+100)]
            if any(word in context for word in ["dispute", "incorrect", "wrong", "contest"]):
                is_disputed = True
                dispute_reason = "Amount appears to be disputed in document"
            
            relationship = AmountRelationship(
                amount=amount_value,
                amount_text=amount.value,
                amount_type=amount_type,
                period=period,
                owed_by_id=tenant.id if tenant else None,
                owed_to_id=landlord.id if landlord else None,
                is_disputed=is_disputed,
                dispute_reason=dispute_reason,
                may_be_illegal=may_be_illegal,
                illegality_reason=illegality_reason,
                confidence=amount.confidence,
            )
            relationships.append(relationship)
        
        reasoning.add_step(
            ReasoningType.ENTITY_RELATIONSHIP,
            f"Built {len(relationships)} financial relationships",
            {},
            {
                "total_amount": sum(r.amount for r in relationships),
                "types": list(set(r.amount_type for r in relationships)),
            }
        )
        
        return relationships
    
    def _infer_amount_type(self, amount: ExtractedEntity, text: str) -> str:
        """Infer the type of a monetary amount"""
        text_lower = text.lower()
        pos = amount.start_position
        context_start = max(0, pos - 100)
        context_end = min(len(text), pos + 100)
        context = text_lower[context_start:context_end]
        
        for amount_type, type_def in self.amount_contexts.items():
            for pattern in type_def["patterns"]:
                if re.search(pattern, context, re.IGNORECASE):
                    return amount_type
        
        return "unknown"
    
    def _get_period_for_type(self, amount_type: str) -> str:
        """Get the period for an amount type"""
        type_def = self.amount_contexts.get(amount_type, {})
        return type_def.get("period", "unknown")
    
    def _identify_primary_property(self, addresses: List[ExtractedEntity],
                                   text: str,
                                   reasoning: ReasoningChain) -> Optional[str]:
        """Identify the primary property address"""
        if not addresses:
            return None
        
        text_lower = text.lower()
        
        # Score each address
        scored = []
        for addr in addresses:
            score = 0
            pos = addr.start_position
            context = text_lower[max(0, pos-100):pos+len(addr.value)+100]
            
            # Boost for property-related keywords
            if any(word in context for word in ["premises", "property", "located at", "subject property"]):
                score += 20
            
            # Boost for being early in document
            if pos < 500:
                score += 10
            
            # Boost for MN address
            if "mn" in addr.value.lower() or "minnesota" in addr.value.lower():
                score += 15
            
            # Boost for having unit number
            if any(term in addr.value.lower() for term in ["apt", "unit", "suite", "#"]):
                score += 10
            
            scored.append((addr, score))
        
        # Return highest scoring
        scored.sort(key=lambda x: x[1], reverse=True)
        primary = scored[0][0].value if scored else None
        
        reasoning.add_step(
            ReasoningType.ENTITY_RELATIONSHIP,
            f"Identified primary property: {primary[:50] if primary else 'None'}...",
            {},
            {"address_count": len(addresses)},
        )
        
        return primary
    
    def _enhance_timeline(self, timeline: List[TimelineEntry],
                          entities: List[ExtractedEntity],
                          reasoning: ReasoningChain) -> List[TimelineEntry]:
        """Enhance timeline entries with related entities"""
        # Get deadline entities
        deadlines = [e for e in entities if e.entity_type == EntityType.DEADLINE]
        
        for deadline in deadlines:
            # Check if already in timeline
            if not any(t.source_text and deadline.value in t.source_text for t in timeline):
                # Parse relative deadline
                match = re.search(r"(\d+)\s*(?:days?|business\s*days?)", deadline.value, re.IGNORECASE)
                if match:
                    days = int(match.group(1))
                    entry = TimelineEntry(
                        event_date=date.today() + timedelta(days=days),
                        date_text=deadline.value,
                        event_type="deadline",
                        title=f"Deadline: {deadline.value}",
                        is_deadline=True,
                        confidence=deadline.confidence,
                        source_text=deadline.value,
                    )
                    timeline.append(entry)
        
        # Sort timeline by date
        timeline.sort(key=lambda t: t.event_date or date.max)
        
        reasoning.add_step(
            ReasoningType.TEMPORAL_LOGIC,
            f"Enhanced timeline with {len(timeline)} entries",
            {},
            {
                "deadlines": sum(1 for t in timeline if t.is_deadline),
                "court_dates": sum(1 for t in timeline if t.is_court_date),
            }
        )
        
        return timeline
    
    def _link_by_proximity(self, entities: List[ExtractedEntity],
                           text: str, reasoning: ReasoningChain):
        """Link entities that appear near each other"""
        proximity_threshold = 200  # characters
        
        links_created = 0
        
        for i, entity_a in enumerate(entities):
            for entity_b in entities[i+1:]:
                # Calculate distance
                dist = abs(entity_a.start_position - entity_b.start_position)
                
                if dist <= proximity_threshold:
                    # Don't link same types (usually)
                    if entity_a.entity_type == entity_b.entity_type:
                        continue
                    
                    # Create bidirectional link
                    if entity_b.id not in entity_a.related_entities:
                        entity_a.related_entities.append(entity_b.id)
                        links_created += 1
                    if entity_a.id not in entity_b.related_entities:
                        entity_b.related_entities.append(entity_a.id)
        
        reasoning.add_step(
            ReasoningType.ENTITY_RELATIONSHIP,
            f"Created {links_created} proximity-based links",
            {"threshold": proximity_threshold},
            {}
        )
    
    def get_party_summary(self, rel_map: RelationshipMap) -> Dict[str, Any]:
        """Get summary of parties and their relationships"""
        return {
            "tenant": rel_map.get_tenant().value if rel_map.get_tenant() else None,
            "landlord": rel_map.get_landlord().value if rel_map.get_landlord() else None,
            "all_parties": [
                {
                    "name": p.value,
                    "role": p.attributes.get("role", "unknown"),
                }
                for p in rel_map.parties
            ],
            "relationships": [
                {
                    "from": r.party_a_name,
                    "to": r.party_b_name,
                    "type": r.relationship_type,
                }
                for r in rel_map.party_relationships
            ]
        }
    
    def get_financial_summary(self, rel_map: RelationshipMap) -> Dict[str, Any]:
        """Get summary of financial relationships"""
        total_owed = sum(
            r.amount for r in rel_map.amount_relationships 
            if r.amount_type in ["rent_owed", "damages", "late_fee", "total_owed"]
        )
        
        disputed = [r for r in rel_map.amount_relationships if r.is_disputed]
        questionable = [r for r in rel_map.amount_relationships if r.may_be_illegal]
        
        return {
            "total_claimed": total_owed,
            "amounts_by_type": {
                r.amount_type: r.amount 
                for r in rel_map.amount_relationships
            },
            "disputed_amounts": [
                {"amount": r.amount, "reason": r.dispute_reason}
                for r in disputed
            ],
            "questionable_amounts": [
                {"amount": r.amount, "type": r.amount_type, "reason": r.illegality_reason}
                for r in questionable
            ],
        }


# Import for type hints
from datetime import timedelta
