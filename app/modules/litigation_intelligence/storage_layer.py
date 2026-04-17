"""
Storage Layer - PostgreSQL Database for Litigation Intelligence
=====================================================

Persistent storage layer for litigation intelligence system.
Handles case data, entity relationships, and intelligence reports.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import json
import asyncio

try:
    import asyncpg
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    logging.warning("asyncpg not available - PostgreSQL storage disabled")

logger = logging.getLogger(__name__)

@dataclass
class LitigationCase:
    """Litigation case data structure."""
    case_id: str
    case_number: str
    case_title: str
    case_type: str
    court: str
    filing_date: datetime
    status: str
    parties: Dict[str, Any]
    documents: List[Dict[str, Any]]
    intelligence_report: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

@dataclass
class EntityRecord:
    """Entity record for tracking legal entities."""
    entity_id: str
    original_name: str
    normalized_name: str
    entity_type: str
    aliases: List[str]
    attributes: Dict[str, Any]
    relationships: List[str]
    confidence: float
    created_at: datetime
    updated_at: datetime

class LitigationStorageLayer:
    """PostgreSQL storage layer for litigation intelligence."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
        self.connection = None
        
    async def initialize(self):
        """Initialize database connection and create tables."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - using in-memory storage")
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            # Create tables if they don't exist
            await self._create_tables()
            
            logger.info("Litigation storage layer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage layer: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables if they don't exist."""
        async with self.pool.acquire() as conn:
            # Cases table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS litigation_cases (
                    case_id VARCHAR(255) PRIMARY KEY,
                    case_number VARCHAR(255) NOT NULL,
                    case_title TEXT NOT NULL,
                    case_type VARCHAR(100) NOT NULL,
                    court VARCHAR(255) NOT NULL,
                    filing_date TIMESTAMP NOT NULL,
                    status VARCHAR(100) NOT NULL,
                    parties JSONB,
                    documents JSONB,
                    intelligence_report JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Entities table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS litigation_entities (
                    entity_id VARCHAR(255) PRIMARY KEY,
                    original_name VARCHAR(255) NOT NULL,
                    normalized_name VARCHAR(255) NOT NULL,
                    entity_type VARCHAR(100) NOT NULL,
                    aliases JSONB,
                    attributes JSONB,
                    relationships JSONB,
                    confidence FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Entity relationships table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS entity_relationships (
                    relationship_id SERIAL PRIMARY KEY,
                    source_entity_id VARCHAR(255) NOT NULL REFERENCES litigation_entities(entity_id),
                    target_entity_id VARCHAR(255) NOT NULL REFERENCES litigation_entities(entity_id),
                    relationship_type VARCHAR(100) NOT NULL,
                    weight FLOAT DEFAULT 1.0,
                    attributes JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Pattern matches table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_matches (
                    match_id SERIAL PRIMARY KEY,
                    case_id VARCHAR(255) NOT NULL REFERENCES litigation_cases(case_id),
                    pattern_type VARCHAR(100) NOT NULL,
                    confidence FLOAT NOT NULL,
                    description TEXT,
                    affected_parties JSONB,
                    legal_basis TEXT,
                    precedent_cases JSONB,
                    recommended_actions JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_case_number ON litigation_cases(case_number)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_case_type ON litigation_cases(case_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON litigation_entities(entity_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_normalized ON litigation_entities(normalized_name)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON entity_relationships(source_entity_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON entity_relationships(target_entity_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_case ON pattern_matches(case_id)")
            
            logger.info("Database tables and indexes created")
    
    async def store_case(self, case_data: Dict[str, Any]) -> str:
        """Store a litigation case."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - case storage disabled")
            return "mock_case_id"
        
        try:
            async with self.pool.acquire() as conn:
                case_id = case_data.get("case_number", f"case_{datetime.now().timestamp()}")
                
                await conn.execute("""
                    INSERT INTO litigation_cases (
                        case_id, case_number, case_title, case_type, court,
                        filing_date, status, parties, documents, intelligence_report
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (case_id) DO UPDATE SET
                        case_title = EXCLUDED.case_title,
                        case_type = EXCLUDED.case_type,
                        court = EXCLUDED.court,
                        filing_date = EXCLUDED.filing_date,
                        status = EXCLUDED.status,
                        parties = EXCLUDED.parties,
                        documents = EXCLUDED.documents,
                        intelligence_report = EXCLUDED.intelligence_report,
                        updated_at = CURRENT_TIMESTAMP
                """, 
                    case_id,
                    case_data.get("case_number", case_id),
                    case_data.get("case_title", ""),
                    case_data.get("case_type", "general"),
                    case_data.get("court", "unknown"),
                    case_data.get("filing_date", datetime.now(timezone.utc)),
                    case_data.get("status", "active"),
                    json.dumps(case_data.get("parties", {})),
                    json.dumps(case_data.get("documents", [])),
                    json.dumps(case_data.get("intelligence_report", {}))
                )
                
                logger.info(f"Stored case {case_id}")
                return case_id
                
        except Exception as e:
            logger.error(f"Failed to store case: {e}")
            raise
    
    async def store_entity(self, entity_data: Dict[str, Any]) -> str:
        """Store an entity record."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - entity storage disabled")
            return "mock_entity_id"
        
        try:
            async with self.pool.acquire() as conn:
                entity_id = entity_data.get("id", f"entity_{datetime.now().timestamp()}")
                
                await conn.execute("""
                    INSERT INTO litigation_entities (
                        entity_id, original_name, normalized_name, entity_type,
                        aliases, attributes, relationships, confidence
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (entity_id) DO UPDATE SET
                        original_name = EXCLUDED.original_name,
                        normalized_name = EXCLUDED.normalized_name,
                        entity_type = EXCLUDED.entity_type,
                        aliases = EXCLUDED.aliases,
                        attributes = EXCLUDED.attributes,
                        relationships = EXCLUDED.relationships,
                        confidence = EXCLUDED.confidence,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    entity_id,
                    entity_data.get("original_name", ""),
                    entity_data.get("normalized_name", ""),
                    entity_data.get("entity_type", "general"),
                    json.dumps(entity_data.get("aliases", [])),
                    json.dumps(entity_data.get("attributes", {})),
                    json.dumps(entity_data.get("relationships", [])),
                    entity_data.get("confidence", 0.5)
                )
                
                logger.info(f"Stored entity {entity_id}")
                return entity_id
                
        except Exception as e:
            logger.error(f"Failed to store entity: {e}")
            raise
    
    async def store_pattern_match(self, case_id: str, pattern_data: Dict[str, Any]) -> str:
        """Store a pattern match record."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - pattern storage disabled")
            return "mock_pattern_id"
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_matches (
                        case_id, pattern_type, confidence, description,
                        affected_parties, legal_basis, precedent_cases, recommended_actions
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    case_id,
                    pattern_data.get("pattern_type", "unknown"),
                    pattern_data.get("confidence", 0.0),
                    pattern_data.get("description", ""),
                    json.dumps(pattern_data.get("affected_parties", [])),
                    pattern_data.get("legal_basis", ""),
                    json.dumps(pattern_data.get("precedent_cases", [])),
                    json.dumps(pattern_data.get("recommended_actions", []))
                )
                
                logger.info(f"Stored pattern match for case {case_id}")
                return "pattern_match_id"
                
        except Exception as e:
            logger.error(f"Failed to store pattern match: {e}")
            raise
    
    async def store_entity_relationship(self, source_id: str, target_id: str,
                                    relationship_type: str, weight: float = 1.0,
                                    attributes: Dict[str, Any] = None) -> str:
        """Store an entity relationship."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - relationship storage disabled")
            return "mock_relationship_id"
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO entity_relationships (
                        source_entity_id, target_entity_id, relationship_type, weight, attributes
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                    source_id, target_id, relationship_type, weight,
                    json.dumps(attributes or {})
                )
                
                logger.info(f"Stored relationship {source_id} -> {target_id}")
                return "relationship_id"
                
        except Exception as e:
            logger.error(f"Failed to store relationship: {e}")
            raise
    
    async def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a litigation case."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - case retrieval disabled")
            return None
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT * FROM litigation_cases WHERE case_id = $1
                """, case_id)
                
                if result:
                    case_dict = dict(result)
                    case_dict["parties"] = json.loads(case_dict["parties"] or "{}")
                    case_dict["documents"] = json.loads(case_dict["documents"] or "[]")
                    case_dict["intelligence_report"] = json.loads(case_dict["intelligence_report"] or "{}")
                    return case_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve case {case_id}: {e}")
            return None
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an entity record."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - entity retrieval disabled")
            return None
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT * FROM litigation_entities WHERE entity_id = $1
                """, entity_id)
                
                if result:
                    entity_dict = dict(result)
                    entity_dict["aliases"] = json.loads(entity_dict["aliases"] or "[]")
                    entity_dict["attributes"] = json.loads(entity_dict["attributes"] or "{}")
                    entity_dict["relationships"] = json.loads(entity_dict["relationships"] or "[]")
                    return entity_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve entity {entity_id}: {e}")
            return None
    
    async def search_cases(self, filters: Dict[str, Any] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Search litigation cases with filters."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - case search disabled")
            return []
        
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM litigation_cases WHERE 1=1"
                params = []
                
                if filters:
                    if "case_type" in filters:
                        query += " AND case_type = $" + str(len(params) + 1)
                        params.append(filters["case_type"])
                    
                    if "status" in filters:
                        query += " AND status = $" + str(len(params) + 1)
                        params.append(filters["status"])
                    
                    if "date_from" in filters:
                        query += " AND filing_date >= $" + str(len(params) + 1)
                        params.append(filters["date_from"])
                    
                    if "date_to" in filters:
                        query += " AND filing_date <= $" + str(len(params) + 1)
                        params.append(filters["date_to"])
                
                query += " ORDER BY filing_date DESC LIMIT $" + str(len(params) + 1)
                params.append(limit)
                
                results = await conn.fetch(query, *params)
                
                cases = []
                for result in results:
                    case_dict = dict(result)
                    case_dict["parties"] = json.loads(case_dict["parties"] or "{}")
                    case_dict["documents"] = json.loads(case_dict["documents"] or "[]")
                    case_dict["intelligence_report"] = json.loads(case_dict["intelligence_report"] or "{}")
                    cases.append(case_dict)
                
                return cases
                
        except Exception as e:
            logger.error(f"Failed to search cases: {e}")
            return []
    
    async def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for an entity."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - relationship retrieval disabled")
            return []
        
        try:
            async with self.pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT er.*, 
                           e1.normalized_name as source_name,
                           e2.normalized_name as target_name
                    FROM entity_relationships er
                    JOIN litigation_entities e1 ON er.source_entity_id = e1.entity_id
                    JOIN litigation_entities e2 ON er.target_entity_id = e2.entity_id
                    WHERE er.source_entity_id = $1 OR er.target_entity_id = $1
                    ORDER BY er.weight DESC
                """, entity_id, entity_id)
                
                relationships = []
                for result in results:
                    rel_dict = dict(result)
                    rel_dict["attributes"] = json.loads(rel_dict["attributes"] or "{}")
                    relationships.append(rel_dict)
                
                return relationships
                
        except Exception as e:
            logger.error(f"Failed to get relationships for {entity_id}: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL not available - statistics disabled")
            return {}
        
        try:
            async with self.pool.acquire() as conn:
                # Case statistics
                case_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_cases,
                        COUNT(DISTINCT case_type) as case_types,
                        COUNT(DISTINCT court) as courts
                    FROM litigation_cases
                """)
                
                # Entity statistics
                entity_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_entities,
                        COUNT(DISTINCT entity_type) as entity_types
                    FROM litigation_entities
                """)
                
                # Pattern statistics
                pattern_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_patterns,
                        COUNT(DISTINCT pattern_type) as pattern_types
                    FROM pattern_matches
                """)
                
                return {
                    "cases": dict(case_stats) if case_stats else {},
                    "entities": dict(entity_stats) if entity_stats else {},
                    "patterns": dict(pattern_stats) if pattern_stats else {},
                    "storage_type": "postgresql" if POSTGRESQL_AVAILABLE else "memory"
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    async def close(self):
        """Close database connection."""
        if self.pool:
            await self.pool.close()
            logger.info("Litigation storage layer closed")

# Factory function
def create_storage_layer(connection_string: str) -> LitigationStorageLayer:
    """Create storage layer instance."""
    return LitigationStorageLayer(connection_string)

# Example usage
async def example_usage():
    """Example usage of storage layer."""
    storage = create_storage_layer("postgresql://user:password@localhost/semptify_lis")
    
    await storage.initialize()
    
    # Store a case
    case_data = {
        "case_number": "27-CV-21-12345",
        "case_title": "Eviction for non-payment",
        "case_type": "eviction",
        "court": "Hennepin County",
        "filing_date": datetime.now(timezone.utc),
        "status": "active",
        "parties": {
            "landlord": "Professional Properties LLC",
            "tenant": "John Doe"
        },
        "documents": [
            {"type": "lease_agreement", "date": "2023-01-01"}
        ]
    }
    
    case_id = await storage.store_case(case_data)
    print(f"Stored case: {case_id}")
    
    # Store an entity
    entity_data = {
        "original_name": "Professional Properties LLC",
        "normalized_name": "Professional Properties LLC",
        "entity_type": "property_llc",
        "aliases": ["Professional Properties", "Professional Props LLC"],
        "attributes": {"type": "apartment_complex", "units": 150},
        "relationships": ["case_12345"],
        "confidence": 0.9
    }
    
    entity_id = await storage.store_entity(entity_data)
    print(f"Stored entity: {entity_id}")
    
    # Get statistics
    stats = await storage.get_statistics()
    print(f"Storage statistics: {stats}")
    
    await storage.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
