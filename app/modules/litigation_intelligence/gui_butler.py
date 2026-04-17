"""
GUI Butler Integration - Interface with Existing GUI System
=====================================================

Integrates Litigation Intelligence System with Semptify's existing GUI Butler.
Provides seamless interface for accessing LIS features through the main application.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import json
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class ButlerCommand:
    """GUI Butler command for LIS integration."""
    command_id: str
    command_type: str
    description: str
    parameters: Dict[str, Any]
    handler: str
    icon: str
    category: str

@dataclass
class ButlerResponse:
    """Response from GUI Butler integration."""
    command_id: str
    success: bool
    data: Dict[str, Any]
    message: str
    timestamp: datetime

class GUIButlerIntegration:
    """Main GUI Butler integration for Litigation Intelligence System."""
    
    def __init__(self):
        self.command_registry = self._initialize_command_registry()
        self.active_sessions = {}
        self.integration_handlers = {}
        
    def _initialize_command_registry(self) -> Dict[str, ButlerCommand]:
        """Initialize command registry for LIS features."""
        return {
            # Court Scraper Commands
            "scrape_mncis": ButlerCommand(
                command_id="scrape_mncis",
                command_type="scrape",
                description="Scrape MN Court Information System",
                parameters={
                    "case_number": {"type": "string", "required": False},
                    "attorney_name": {"type": "string", "required": False},
                    "date_range": {"type": "string", "required": False}
                },
                handler="court_scraper",
                icon="🏛",
                category="court_scraping"
            ),
            "scrape_efilemn": ButlerCommand(
                command_id="scrape_efilemn",
                command_type="scrape",
                description="Scrape Minnesota eFileMN system",
                parameters={
                    "case_number": {"type": "string", "required": False},
                    "party_name": {"type": "string", "required": False}
                },
                handler="court_scraper",
                icon="📁",
                category="court_scraping"
            ),
            "get_efilemn_filings": ButlerCommand(
                command_id="get_efilemn_filings",
                command_type="query",
                description="Get specific case filings from eFileMN",
                parameters={
                    "case_number": {"type": "string", "required": True}
                },
                handler="court_scraper",
                icon="📋",
                category="court_scraping"
            ),
            
            # Entity Normalizer Commands
            "normalize_entity": ButlerCommand(
                command_id="normalize_entity",
                command_type="normalize",
                description="Normalize entity name to canonical form",
                parameters={
                    "entity_name": {"type": "string", "required": True},
                    "context": {"type": "string", "required": False, "default": "general"}
                },
                handler="entity_normalizer",
                icon="🔍",
                category="entity_resolution"
            ),
            "resolve_entities": ButlerCommand(
                command_id="resolve_entities",
                command_type="batch_normalize",
                description="Resolve multiple entities to normalized forms",
                parameters={
                    "entities": {"type": "array", "required": True},
                    "context": {"type": "string", "required": False, "default": "general"}
                },
                handler="entity_normalizer",
                icon="👥",
                category="entity_resolution"
            ),
            "get_entity_relationships": ButlerCommand(
                command_id="get_entity_relationships",
                command_type="query",
                description="Get relationships between normalized entities",
                parameters={
                    "entities": {"type": "array", "required": True}
                },
                handler="entity_normalizer",
                icon="🔗",
                category="entity_resolution"
            ),
            
            # Intelligence Engine Commands
            "analyze_case": ButlerCommand(
                command_id="analyze_case",
                command_type="analyze",
                description="Analyze case for patterns and intelligence",
                parameters={
                    "case_data": {"type": "object", "required": True}
                },
                handler="intelligence_engine",
                icon="🧠",
                category="intelligence_analysis"
            ),
            "get_case_intelligence": ButlerCommand(
                command_id="get_case_intelligence",
                command_type="query",
                description="Get stored intelligence report for a case",
                parameters={
                    "case_id": {"type": "string", "required": True}
                },
                handler="intelligence_engine",
                icon="📊",
                category="intelligence_analysis"
            ),
            "get_pattern_statistics": ButlerCommand(
                command_id="get_pattern_statistics",
                command_type="query",
                description="Get statistics on detected patterns",
                parameters={},
                handler="intelligence_engine",
                icon="📈",
                category="intelligence_analysis"
            ),
            
            # Graph Engine Commands
            "build_entity_graph": ButlerCommand(
                command_id="build_entity_graph",
                command_type="graph_build",
                description="Build entity relationship graph",
                parameters={
                    "entities": {"type": "array", "required": True},
                    "relationships": {"type": "array", "required": False}
                },
                handler="graph_engine",
                icon="🕸️",
                category="graph_visualization"
            ),
            "find_shortest_path": ButlerCommand(
                command_id="find_shortest_path",
                command_type="graph_query",
                description="Find shortest path between entities",
                parameters={
                    "source_entity": {"type": "string", "required": True},
                    "target_entity": {"type": "string", "required": True}
                },
                handler="graph_engine",
                icon="🛤",
                category="graph_visualization"
            ),
            "generate_graph_visualization": ButlerCommand(
                command_id="generate_graph_visualization",
                command_type="graph_viz",
                description="Generate graph visualization",
                parameters={
                    "format": {"type": "string", "required": False, "default": "png"}
                },
                handler="graph_engine",
                icon="🎨",
                category="graph_visualization"
            ),
            
            # Storage Layer Commands
            "store_case": ButlerCommand(
                command_id="store_case",
                command_type="store",
                description="Store litigation case data",
                parameters={
                    "case_data": {"type": "object", "required": True}
                },
                handler="storage_layer",
                icon="💾",
                category="data_storage"
            ),
            "store_entity": ButlerCommand(
                command_id="store_entity",
                command_type="store",
                description="Store entity data",
                parameters={
                    "entity_data": {"type": "object", "required": True}
                },
                handler="storage_layer",
                icon="🗃",
                category="data_storage"
            ),
            "search_cases": ButlerCommand(
                command_id="search_cases",
                command_type="query",
                description="Search litigation cases",
                parameters={
                    "filters": {"type": "object", "required": False},
                    "limit": {"type": "integer", "required": False, "default": 100}
                },
                handler="storage_layer",
                icon="🔍",
                category="data_storage"
            ),
            "get_case_statistics": ButlerCommand(
                command_id="get_case_statistics",
                command_type="query",
                description="Get litigation case statistics",
                parameters={},
                handler="storage_layer",
                icon="📊",
                category="data_storage"
            ),
            
            # Reporting Layer Commands
            "generate_case_summary": ButlerCommand(
                command_id="generate_case_summary",
                command_type="report",
                description="Generate comprehensive case summary report",
                parameters={
                    "time_period": {"type": "string", "required": False, "default": "30_days"},
                    "filters": {"type": "object", "required": False}
                },
                handler="reporting_layer",
                icon="📋",
                category="reporting"
            ),
            "generate_entity_analysis": ButlerCommand(
                command_id="generate_entity_analysis",
                command_type="report",
                description="Generate entity analysis report",
                parameters={
                    "time_period": {"type": "string", "required": False, "default": "30_days"},
                    "entity_type": {"type": "string", "required": False}
                },
                handler="reporting_layer",
                icon="👥",
                category="reporting"
            ),
            "generate_pattern_trends": ButlerCommand(
                command_id="generate_pattern_trends",
                command_type="report",
                description="Generate pattern trends report",
                parameters={
                    "time_period": {"type": "string", "required": False, "default": "90_days"}
                },
                handler="reporting_layer",
                icon="📈",
                category="reporting"
            )
        }
    
    async def execute_command(self, command_id: str, parameters: Dict[str, Any],
                        session_id: str = None) -> ButlerResponse:
        """Execute a GUI Butler command."""
        if command_id not in self.command_registry:
            return ButlerResponse(
                command_id=command_id,
                success=False,
                data={},
                message=f"Unknown command: {command_id}",
                timestamp=datetime.now(timezone.utc)
            )
        
        command = self.command_registry[command_id]
        
        try:
            # Log command execution
            logger.info(f"Executing LIS command: {command_id} with parameters: {parameters}")
            
            # Execute command based on handler
            if command.handler == "court_scraper":
                result = await self._handle_court_scraper_command(command, parameters)
            elif command.handler == "entity_normalizer":
                result = await self._handle_entity_normalizer_command(command, parameters)
            elif command.handler == "intelligence_engine":
                result = await self._handle_intelligence_engine_command(command, parameters)
            elif command.handler == "graph_engine":
                result = await self._handle_graph_engine_command(command, parameters)
            elif command.handler == "storage_layer":
                result = await self._handle_storage_layer_command(command, parameters)
            elif command.handler == "reporting_layer":
                result = await self._handle_reporting_layer_command(command, parameters)
            else:
                raise ValueError(f"Unknown handler: {command.handler}")
            
            return ButlerResponse(
                command_id=command_id,
                success=True,
                data=result,
                message=f"Command {command_id} executed successfully",
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Command {command_id} failed: {e}")
            return ButlerResponse(
                command_id=command_id,
                success=False,
                data={},
                message=f"Command failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _handle_court_scraper_command(self, command: ButlerCommand,
                                        parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle court scraper commands."""
        from .court_scraper import create_court_scraper
        
        scraper = create_court_scraper()
        
        if command.command_id == "scrape_mncis":
            cases = await scraper.scrape_mncis_cases(
                case_number=parameters.get("case_number"),
                attorney_name=parameters.get("attorney_name"),
                date_range=parameters.get("date_range")
            )
            return {"cases": cases, "source": "mncis"}
        
        elif command.command_id == "scrape_efilemn":
            cases = await scraper.scrape_efilemn_cases(
                case_number=parameters.get("case_number"),
                party_name=parameters.get("party_name")
            )
            return {"cases": cases, "source": "efilemn"}
        
        elif command.command_id == "get_efilemn_filings":
            filings = await scraper.scrape_efilemn_filings(
                case_number=parameters["case_number"]
            )
            return {"filings": filings, "source": "efilemn"}
        
        return {}
    
    async def _handle_entity_normalizer_command(self, command: ButlerCommand,
                                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle entity normalizer commands."""
        from .entity_normalizer import create_entity_normalizer
        
        normalizer = create_entity_normalizer()
        
        if command.command_id == "normalize_entity":
            result = normalizer.normalize_entity(
                parameters["entity_name"],
                parameters.get("context", "general")
            )
            return {"resolution": result.to_dict()}
        
        elif command.command_id == "resolve_entities":
            results = normalizer.resolve_entities(
                parameters["entities"],
                parameters.get("context", "general")
            )
            relationships = normalizer.get_entity_relationships(results)
            return {"resolutions": [r.to_dict() for r in results], "relationships": relationships}
        
        elif command.command_id == "get_entity_relationships":
            # This would need entity data from storage
            return {"message": "Entity relationships query requires storage integration"}
        
        return {}
    
    async def _handle_intelligence_engine_command(self, command: ButlerCommand,
                                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle intelligence engine commands."""
        from .intelligence_engine import create_intelligence_engine
        
        engine = create_intelligence_engine()
        
        if command.command_id == "analyze_case":
            report = await engine.analyze_case(parameters["case_data"])
            return {"intelligence_report": report.__dict__}
        
        elif command.command_id == "get_case_intelligence":
            report = engine.get_case_intelligence(parameters["case_id"])
            return {"intelligence_report": report.__dict__ if report else {}}
        
        elif command.command_id == "get_pattern_statistics":
            stats = engine.get_pattern_statistics()
            return {"statistics": stats}
        
        return {}
    
    async def _handle_graph_engine_command(self, command: ButlerCommand,
                                       parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle graph engine commands."""
        from .graph_engine import create_graph_engine
        
        graph_engine = create_graph_engine()
        
        if command.command_id == "build_entity_graph":
            graph_engine.build_from_entities(parameters["entities"])
            relationships = parameters.get("relationships", [])
            for rel in relationships:
                if isinstance(rel, dict):
                    graph_engine.add_relationship(
                        rel["source"], rel["target"],
                        rel.get("type", "related_to"),
                        rel.get("weight", 1.0),
                        rel.get("attributes", {})
                    )
            
            graph_data = graph_engine.export_graph_data()
            return {"graph_data": graph_data}
        
        elif command.command_id == "find_shortest_path":
            path = graph_engine.find_shortest_path(
                parameters["source_entity"],
                parameters["target_entity"]
            )
            return {"path": path}
        
        elif command.command_id == "generate_graph_visualization":
            viz_data = graph_engine.generate_visualization(
                parameters.get("format", "png")
            )
            return {"visualization": viz_data}
        
        return {}
    
    async def _handle_storage_layer_command(self, command: ButlerCommand,
                                       parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storage layer commands."""
        from .storage_layer import create_storage_layer
        
        # This would need database connection string
        # For now, return mock responses
        if command.command_id == "store_case":
            return {"case_id": f"stored_case_{datetime.now().timestamp()}"}
        
        elif command.command_id == "store_entity":
            return {"entity_id": f"stored_entity_{datetime.now().timestamp()}"}
        
        elif command.command_id == "search_cases":
            return {"cases": [], "total": 0}
        
        elif command.command_id == "get_case_statistics":
            return {"statistics": {"total_cases": 0, "storage_type": "mock"}}
        
        return {}
    
    async def _handle_reporting_layer_command(self, command: ButlerCommand,
                                        parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reporting layer commands."""
        from .reporting_layer import create_reporting_layer
        
        reporting = create_reporting_layer()
        
        if command.command_id == "generate_case_summary":
            report = await reporting.generate_case_summary_report(
                parameters.get("time_period", "30_days"),
                parameters.get("filters")
            )
            return {"report": report.__dict__}
        
        elif command.command_id == "generate_entity_analysis":
            report = await reporting.generate_entity_analysis_report(
                parameters.get("time_period", "30_days"),
                parameters.get("entity_type")
            )
            return {"report": report.__dict__}
        
        elif command.command_id == "generate_pattern_trends":
            report = await reporting.generate_pattern_trends_report(
                parameters.get("time_period", "90_days")
            )
            return {"report": report.__dict__}
        
        return {}
    
    def get_available_commands(self) -> List[ButlerCommand]:
        """Get list of available commands."""
        return list(self.command_registry.values())
    
    def get_commands_by_category(self, category: str) -> List[ButlerCommand]:
        """Get commands filtered by category."""
        return [cmd for cmd in self.command_registry.values() if cmd.category == category]
    
    def register_session(self, session_id: str, user_context: Dict[str, Any]):
        """Register a new GUI Butler session."""
        self.active_sessions[session_id] = {
            "user_context": user_context,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        logger.info(f"Registered GUI Butler session: {session_id}")
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get active session information."""
        return self.active_sessions.get(session_id)
    
    def update_session_activity(self, session_id: str):
        """Update session activity timestamp."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.now(timezone.utc)
    
    def cleanup_sessions(self, max_age_hours: int = 24):
        """Clean up old sessions."""
        current_time = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            age_hours = (current_time - session_data["created_at"]).total_seconds() / 3600
            if age_hours > max_age_hours:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired GUI Butler sessions")

# Factory function
def create_gui_butler() -> GUIButlerIntegration:
    """Create GUI Butler integration instance."""
    return GUIButlerIntegration()

# Example usage
async def example_usage():
    """Example usage of GUI Butler integration."""
    butler = create_gui_butler()
    
    # Register session
    session_id = "test_session_123"
    butler.register_session(session_id, {"user_id": "test_user", "role": "tenant_advocate"})
    
    # Get available commands
    commands = butler.get_available_commands()
    print(f"Available commands: {len(commands)}")
    
    # Execute a command
    response = await butler.execute_command(
        "analyze_case",
        {"case_data": {"case_number": "27-CV-21-12345", "case_type": "eviction"}},
        session_id
    )
    
    print(f"Command executed: {response.success}")
    print(f"Response: {response.message}")
    
    # Get court scraping commands
    court_commands = butler.get_commands_by_category("court_scraping")
    print(f"Court scraping commands: {len(court_commands)}")
    
    # Cleanup
    butler.cleanup_sessions()

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
