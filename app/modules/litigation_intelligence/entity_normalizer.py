"""
Entity Normalization Engine - Legal Entity Resolution
===========================================

Resolves messy naming variations for legal entities in housing cases.
Handles attorneys, properties, LLCs, and other legal entities.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

@dataclass
class EntityResolution:
    """Result of entity normalization."""
    original_name: str
    normalized_name: str
    entity_type: str
    confidence: float
    aliases: List[str]
    metadata: Dict[str, Any]

class EntityNormalizer:
    """Normalizes and resolves legal entity names."""
    
    def __init__(self):
        # Load entity databases
        self.attorney_aliases = self._load_attorney_database()
        self.property_llc_patterns = self._load_property_patterns()
        self.developer_llc_patterns = self._load_developer_patterns()
        self.entity_cache = {}
        
    def _load_attorney_database(self) -> Dict[str, Dict[str, Any]]:
        """Load attorney name database and aliases."""
        return {
            # Common variations and misspellings
            "david schooler": {
                "canonical": "David A. Schooler",
                "aliases": ["David Schooler", "D.A. Schooler", "David Schooler Law"],
                "firm": "Schooler Law Office",
                "specialties": ["family law", "housing law", "tenant rights"]
            },
            "john smith": {
                "canonical": "John Smith",
                "aliases": ["John P. Smith", "J.P. Smith", "Jonathan Smith"],
                "firm": "Smith & Associates",
                "specialties": ["civil litigation", "real estate law"]
            },
            "mary johnson": {
                "canonical": "Mary Johnson",
                "aliases": ["Mary A. Johnson", "M.A. Johnson", "Mary Johnson Law"],
                "firm": "Johnson Legal Group",
                "specialties": ["tenant rights", "housing discrimination"]
            },
            "robert williams": {
                "canonical": "Robert Williams",
                "aliases": ["Robert P. Williams", "R.P. Williams", "Robert Williams Esq."],
                "firm": "Williams Law Firm",
                "specialties": ["eviction defense", "landlord-tenant law"]
            }
        }
    
    def _load_property_patterns(self) -> List[Dict[str, Any]]:
        """Load property LLC naming patterns."""
        return [
            {
                "pattern": r"(.+)\s+(apartments|apartment|apt|apts?)\s+(llc|l\.l\.c\.|limited)",
                "type": "apartment_complex",
                "example": "Sunset Apartments LLC"
            },
            {
                "pattern": r"(.+)\s+(properties|property|prop)s?\s+(management|mgmt)\s+(llc|l\.l\.c\.|limited)",
                "type": "property_management",
                "example": "Green Valley Properties LLC"
            },
            {
                "pattern": r"(.+)\s+(homes|housing|developments?)\s+(llc|l\.l\.c\.|limited)",
                "type": "housing_development",
                "example": "Maple Grove Homes LLC"
            },
            {
                "pattern": r"(.+)\s+(realty|real\s+estate)\s+(llc|l\.l\.c\.|limited)",
                "type": "real_estate",
                "example": "Northern Realty LLC"
            }
        ]
    
    def _load_developer_patterns(self) -> List[Dict[str, Any]]:
        """Load developer LLC naming patterns."""
        return [
            {
                "pattern": r"(.+)\s+(development|dev)\s+(llc|l\.l\.c\.|limited)",
                "type": "real_estate_development",
                "example": "Harbor View Development LLC"
            },
            {
                "pattern": r"(.+)\s+(construction|builders?|building)\s+(llc|l\.l\.c\.|limited)",
                "type": "construction",
                "example": "Summit Construction LLC"
            },
            {
                "pattern": r"(.+)\s+(investments|inv)\s+(llc|l\.l\.c\.|limited)",
                "type": "investment",
                "example": "Capital Investments LLC"
            }
        ]
    
    def normalize_entity(self, entity_name: str, context: str = "general") -> EntityResolution:
        """
        Normalize an entity name to its canonical form.
        
        Args:
            entity_name: Raw entity name to normalize
            context: Context type (attorney, property, developer, general)
        
        Returns:
            EntityResolution with normalized name and confidence
        """
        # Check cache first
        if entity_name in self.entity_cache:
            return self.entity_cache[entity_name]
        
        # Clean the input
        clean_name = self._clean_entity_name(entity_name)
        
        # Try attorney normalization first
        if context in ["attorney", "lawyer", "counsel"]:
            result = self._normalize_attorney(clean_name)
            if result.confidence > 0.7:
                self.entity_cache[entity_name] = result
                return result
        
        # Try property LLC normalization
        if context in ["property", "landlord", "owner", "llc"]:
            result = self._normalize_property_llc(clean_name)
            if result.confidence > 0.6:
                self.entity_cache[entity_name] = result
                return result
        
        # Try developer LLC normalization
        if context in ["developer", "construction", "builder"]:
            result = self._normalize_developer_llc(clean_name)
            if result.confidence > 0.6:
                self.entity_cache[entity_name] = result
                return result
        
        # General normalization
        result = self._general_normalization(clean_name)
        self.entity_cache[entity_name] = result
        return result
    
    def _clean_entity_name(self, name: str) -> str:
        """Clean entity name for processing."""
        # Remove common legal suffixes
        name = re.sub(r'\s+(esq\.?|attorney|law|law\s+office|firm|group|llc|l\.l\.c\.|limited|inc|corp|co\.?)$', '', name, flags=re.IGNORECASE)
        
        # Remove punctuation and extra spaces
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip().title()
    
    def _normalize_attorney(self, name: str) -> EntityResolution:
        """Normalize attorney names."""
        name_lower = name.lower()
        
        # Check against attorney database
        for canonical_name, attorney_data in self.attorney_aliases.items():
            if name_lower == canonical_name.lower():
                return EntityResolution(
                    original_name=name,
                    normalized_name=attorney_data["canonical"],
                    entity_type="attorney",
                    confidence=1.0,
                    aliases=attorney_data["aliases"],
                    metadata={
                        "firm": attorney_data.get("firm"),
                        "specialties": attorney_data.get("specialties", [])
                    }
                )
            
            # Check aliases
            for alias in attorney_data.get("aliases", []):
                if name_lower == alias.lower():
                    return EntityResolution(
                        original_name=name,
                        normalized_name=attorney_data["canonical"],
                        entity_type="attorney",
                        confidence=0.9,
                        aliases=attorney_data["aliases"],
                        metadata=attorney_data
                    )
        
        # Fuzzy matching for misspellings
        best_match = None
        best_score = 0.6
        
        for canonical_name, attorney_data in self.attorney_aliases.items():
            score = self._fuzzy_match(name_lower, canonical_name.lower())
            if score > best_score:
                best_score = score
                best_match = (canonical_name, attorney_data)
        
        if best_match:
            canonical_name, attorney_data = best_match
            return EntityResolution(
                original_name=name,
                normalized_name=canonical_name,
                entity_type="attorney",
                confidence=best_score,
                aliases=attorney_data.get("aliases", []),
                metadata=attorney_data
            )
        
        # No match found
        return EntityResolution(
            original_name=name,
            normalized_name=name.title(),
            entity_type="attorney",
            confidence=0.3,
            aliases=[],
            metadata={}
        )
    
    def _normalize_property_llc(self, name: str) -> EntityResolution:
        """Normalize property LLC names."""
        name_lower = name.lower()
        
        # Check against property patterns
        for pattern_data in self.property_llc_patterns:
            match = re.match(pattern_data["pattern"], name_lower, re.IGNORECASE)
            if match:
                entity_name = match.group(1).title()
                return EntityResolution(
                    original_name=name,
                    normalized_name=entity_name,
                    entity_type="property_llc",
                    confidence=0.9,
                    aliases=[entity_name],
                    metadata={
                        "llc_type": pattern_data["type"],
                        "pattern_matched": pattern_data["pattern"]
                    }
                )
        
        # No pattern match
        return EntityResolution(
            original_name=name,
            normalized_name=name.title(),
            entity_type="property_llc",
            confidence=0.4,
            aliases=[],
            metadata={}
        )
    
    def _normalize_developer_llc(self, name: str) -> EntityResolution:
        """Normalize developer LLC names."""
        name_lower = name.lower()
        
        # Check against developer patterns
        for pattern_data in self.developer_llc_patterns:
            match = re.match(pattern_data["pattern"], name_lower, re.IGNORECASE)
            if match:
                entity_name = match.group(1).title()
                return EntityResolution(
                    original_name=name,
                    normalized_name=entity_name,
                    entity_type="developer_llc",
                    confidence=0.9,
                    aliases=[entity_name],
                    metadata={
                        "llc_type": pattern_data["type"],
                        "pattern_matched": pattern_data["pattern"]
                    }
                )
        
        # No pattern match
        return EntityResolution(
            original_name=name,
            normalized_name=name.title(),
            entity_type="developer_llc",
            confidence=0.4,
            aliases=[],
            metadata={}
        )
    
    def _general_normalization(self, name: str) -> EntityResolution:
        """General entity normalization."""
        # Remove common business suffixes
        clean_name = re.sub(r'\s+(inc|llc|l\.l\.c\.|limited|corp|co\.?)$', '', name, flags=re.IGNORECASE)
        
        # Standardize capitalization
        normalized_name = ' '.join(word.capitalize() for word in clean_name.split())
        
        return EntityResolution(
            original_name=name,
            normalized_name=normalized_name,
            entity_type="general",
            confidence=0.5,
            aliases=[normalized_name],
            metadata={}
        )
    
    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match score between two strings."""
        if not str1 or not str2:
            return 0.0
        
        # Use SequenceMatcher for fuzzy matching
        matcher = SequenceMatcher(None, str1.lower())
        ratio = matcher.ratio(str2.lower())
        
        return ratio
    
    def resolve_entities(self, entity_names: List[str], context: str = "general") -> List[EntityResolution]:
        """
        Resolve multiple entities to their normalized forms.
        
        Args:
            entity_names: List of entity names to resolve
            context: Context type for resolution
        
        Returns:
            List of EntityResolution objects
        """
        resolutions = []
        
        for entity_name in entity_names:
            resolution = self.normalize_entity(entity_name, context)
            resolutions.append(resolution)
        
        return resolutions
    
    def get_entity_relationships(self, entities: List[EntityResolution]) -> Dict[str, List[str]]:
        """
        Analyze relationships between normalized entities.
        
        Args:
            entities: List of normalized entities
        
        Returns:
            Dictionary mapping entity types to related entities
        """
        relationships = {
            "attorneys": [],
            "properties": [],
            "developers": [],
            "general": []
        }
        
        # Group by entity type
        for entity in entities:
            entity_type = entity.entity_type
            normalized_name = entity.normalized_name
            
            if entity_type == "attorney":
                relationships["attorneys"].append(normalized_name)
            elif entity_type == "property_llc":
                relationships["properties"].append(normalized_name)
            elif entity_type == "developer_llc":
                relationships["developers"].append(normalized_name)
            else:
                relationships["general"].append(normalized_name)
        
        return relationships
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        return {
            "total_entities_processed": len(self.entity_cache),
            "attorney_database_size": len(self.attorney_aliases),
            "property_patterns_count": len(self.property_llc_patterns),
            "developer_patterns_count": len(self.developer_llc_patterns),
            "cache_hit_rate": len(self.entity_cache) / max(1, len(self.entity_cache)) * 100
        }

# Factory function
def create_entity_normalizer() -> EntityNormalizer:
    """Create entity normalizer instance."""
    return EntityNormalizer()

# Example usage
if __name__ == "__main__":
    normalizer = create_entity_normalizer()
    
    # Test attorney normalization
    test_names = [
        "David Schooler",
        "D.A. Schooler", 
        "david schooler law",
        "John P. Smith",
        "Sunset Apartments LLC",
        "Green Valley Properties LLC",
        "Harbor View Development LLC"
    ]
    
    print("Entity Normalization Test Results:")
    print("=" * 50)
    
    for name in test_names:
        result = normalizer.normalize_entity(name, "general")
        print(f"Original: {result.original_name}")
        print(f"Normalized: {result.normalized_name}")
        print(f"Type: {result.entity_type}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Aliases: {', '.join(result.aliases)}")
        print("-" * 30)
    
    # Test entity relationships
    entities = normalizer.resolve_entities(test_names)
    relationships = normalizer.get_entity_relationships(entities)
    
    print("\nEntity Relationships:")
    print("=" * 50)
    for entity_type, related_entities in relationships.items():
        print(f"{entity_type.title()}: {', '.join(related_entities)}")
    
    # Statistics
    stats = normalizer.get_statistics()
    print(f"\nStatistics: {stats}")
