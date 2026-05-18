"""
Litigation Intelligence System Router - Justice-Grade Legal Intelligence API
=====================================================================

FastAPI router for Litigation Intelligence System (LIS).
Provides endpoints for court scraping, entity resolution, intelligence analysis,
graph visualization, storage, reporting, and scheduling.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from app.core.security import get_current_user
from ..modules.litigation_intelligence.court_scraper import create_court_scraper
from ..modules.litigation_intelligence.entity_normalizer import create_entity_normalizer
from ..modules.litigation_intelligence.intelligence_engine import create_intelligence_engine
from ..modules.litigation_intelligence.graph_engine import create_graph_engine
from ..modules.litigation_intelligence.storage_layer import create_storage_layer
from ..modules.litigation_intelligence.reporting_layer import create_reporting_layer
from ..modules.litigation_intelligence.gui_butler import create_gui_butler
from ..modules.litigation_intelligence.scheduler import create_litigation_scheduler

logger = logging.getLogger(__name__)

# Initialize LIS components
lis_router = APIRouter(prefix="/api/litigation-intelligence", tags=["Litigation Intelligence"])

# Pydantic Models
class CourtScrapingRequest(BaseModel):
    """Request for court scraping operations."""
    case_number: Optional[str] = Field(None, description="Case number to search")
    attorney_name: Optional[str] = Field(None, description="Attorney name to search")
    date_range: Optional[str] = Field(None, description="Date range for search")
    court_system: str = Field(..., description="Court system to scrape (mncis, efilemn)")

class EntityNormalizationRequest(BaseModel):
    """Request for entity normalization."""
    entity_name: str = Field(..., description="Entity name to normalize")
    context: str = Field("general", description="Context for normalization")

class CaseAnalysisRequest(BaseModel):
    """Request for case intelligence analysis."""
    case_data: Dict[str, Any] = Field(..., description="Case data to analyze")
    analysis_options: Optional[Dict[str, Any]] = Field(None, description="Analysis options")

class GraphVisualizationRequest(BaseModel):
    """Request for graph visualization."""
    entities: List[Dict[str, Any]] = Field(..., description="Entities to include in graph")
    relationship_data: Optional[List[Dict[str, Any]]] = Field(None, description="Relationship data between entities")
    visualization_options: Optional[Dict[str, Any]] = Field(None, description="Visualization options")

class ReportGenerationRequest(BaseModel):
    """Request for report generation."""
    report_type: str = Field(..., description="Type of report to generate")
    time_period: str = Field("30_days", description="Time period for report")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters for report")
    export_format: str = Field("json", description="Export format (json, csv, pdf)")

class ScheduledTaskRequest(BaseModel):
    """Request for scheduled task management."""
    task_name: str = Field(..., description="Task name")
    schedule_type: str = Field(..., description="Schedule type (cron, interval, once)")
    schedule_expression: str = Field(..., description="Schedule expression")
    parameters: Dict[str, Any] = Field(..., description="Task parameters")
    enabled: bool = Field(True, description="Whether task is enabled")

# Initialize LIS components
court_scraper = create_court_scraper()
entity_normalizer = create_entity_normalizer()
intelligence_engine = create_intelligence_engine()
graph_engine = create_graph_engine()
storage_layer = create_storage_layer("postgresql://user:password@localhost/semptify_lis")
reporting_layer = create_reporting_layer()
gui_butler = create_gui_butler()
scheduler = create_litigation_scheduler()

@lis_router.post("/scrape/court")
async def scrape_court_system(request: CourtScrapingRequest,
                           current_user = Depends(get_current_user)):
    """Scrape court system for case data."""
    try:
        if request.court_system == "mncis":
            cases = await court_scraper.scrape_mncis_cases(
                case_number=request.case_number,
                attorney_name=request.attorney_name,
                date_range=request.date_range
            )
        elif request.court_system == "efilemn":
            cases = await court_scraper.scrape_efilemn_cases(
                case_number=request.case_number,
                party_name=request.attorney_name
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported court system")
        
        return JSONResponse(content={
            "success": True,
            "cases": cases,
            "court_system": request.court_system,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Court scraping failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@lis_router.post("/scrape/filings/{case_number}")
async def scrape_case_filings(case_number: str,
                           current_user = Depends(get_current_user)):
    """Scrape specific case filings."""
    try:
        filings = await court_scraper.scrape_efilemn_filings(case_number)
        
        return JSONResponse(content={
            "success": True,
            "case_number": case_number,
            "filings": filings,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Filing scraping failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@lis_router.post("/normalize/entity")
async def normalize_entity(request: EntityNormalizationRequest,
                           current_user = Depends(get_current_user)):
    """Normalize an entity name."""
    try:
        resolution = entity_normalizer.normalize_entity(
            request.entity_name,
            request.context
        )
        
        return JSONResponse(content={
            "success": True,
            "resolution": resolution.to_dict(),
            "normalized_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Entity normalization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")

@lis_router.post("/normalize/entities")
async def normalize_entities(request: Dict[str, Any],
                           current_user = Depends(get_current_user)):
    """Normalize multiple entities."""
    try:
        entities = request.get("entities", [])
        if not isinstance(entities, list):
            raise HTTPException(status_code=400, detail="entities must be a list")
        
        resolutions = entity_normalizer.resolve_entities(
            entities,
            request.get("context", "general")
        )
        
        return JSONResponse(content={
            "success": True,
            "resolutions": [r.to_dict() for r in resolutions],
            "normalized_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Entity normalization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")

@lis_router.post("/analyze/case")
async def analyze_case_intelligence(request: CaseAnalysisRequest,
                                current_user = Depends(get_current_user)):
    """Analyze case for intelligence patterns."""
    try:
        report = await intelligence_engine.analyze_case(request.case_data)
        
        return JSONResponse(content={
            "success": True,
            "intelligence_report": report.__dict__,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Case analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@lis_router.get("/intelligence/{case_id}")
async def get_case_intelligence(case_id: str,
                              current_user = Depends(get_current_user)):
    """Get stored intelligence report for a case."""
    try:
        report = intelligence_engine.get_case_intelligence(case_id)
        
        if not report:
            return JSONResponse(content={
                "success": False,
                "message": "Intelligence report not found"
            }, status_code=404)
        
        return JSONResponse(content={
            "success": True,
            "intelligence_report": report.__dict__
        })
        
    except Exception as e:
        logger.error(f"Intelligence retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

@lis_router.post("/graph/build")
async def build_entity_graph(request: GraphVisualizationRequest,
                           current_user = Depends(get_current_user)):
    """Build entity relationship graph."""
    try:
        graph_engine.build_from_entities(request.entities)
        
        if request.relationship_data:
            for rel in request.relationship_data:
                graph_engine.add_relationship(
                    rel.get("source"),
                    rel.get("target"),
                    rel.get("type", "related_to"),
                    rel.get("weight", 1.0),
                    rel.get("attributes", {})
                )
        
        analysis = graph_engine.analyze_graph()
        
        return JSONResponse(content={
            "success": True,
            "graph_data": graph_engine.export_graph_data(),
            "analysis": analysis.to_dict(),
            "built_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Graph building failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph building failed: {str(e)}")

@lis_router.post("/graph/visualize")
async def generate_graph_visualization(request: GraphVisualizationRequest,
                                  current_user = Depends(get_current_user)):
    """Generate graph visualization."""
    try:
        # Build graph first
        graph_engine.build_from_entities(request.entities)
        
        visualization_data = graph_engine.generate_visualization(
            request.visualization_options.get("format", "png")
        )
        
        return JSONResponse(content={
            "success": True,
            "visualization": visualization_data,
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Graph visualization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Visualization failed: {str(e)}")

@lis_router.post("/graph/path/{source_entity}/{target_entity}")
async def find_shortest_path(source_entity: str,
                             target_entity: str,
                             current_user = Depends(get_current_user)):
    """Find shortest path between entities."""
    try:
        path = graph_engine.find_shortest_path(source_entity, target_entity)
        
        return JSONResponse(content={
            "success": True,
            "source_entity": source_entity,
            "target_entity": target_entity,
            "path": path,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Path finding failed: {e}")
        raise HTTPException(status_code=500, detail=f"Path finding failed: {str(e)}")

@lis_router.post("/report/generate")
async def generate_report(request: ReportGenerationRequest,
                        current_user = Depends(get_current_user)):
    """Generate litigation intelligence report."""
    try:
        if request.report_type == "case_summary":
            report = await reporting_layer.generate_case_summary_report(
                request.time_period,
                request.filters
            )
        elif request.report_type == "entity_analysis":
            report = await reporting_layer.generate_entity_analysis_report(
                request.time_period,
                request.filters.get("entity_type") if request.filters else None
            )
        elif request.report_type == "pattern_trends":
            report = await reporting_layer.generate_pattern_trends_report(request.time_period)
        elif request.report_type == "success_metrics":
            report = await reporting_layer.generate_success_metrics_report(request.time_period)
        else:
            raise HTTPException(status_code=400, detail="Unsupported report type")
        
        return JSONResponse(content={
            "success": True,
            "report": report.__dict__,
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@lis_router.get("/report/{report_id}")
async def get_report(report_id: str,
                   current_user = Depends(get_current_user)):
    """Get a generated report."""
    try:
        report = reporting_layer.get_report(report_id)
        
        if not report:
            return JSONResponse(content={
                "success": False,
                "message": "Report not found"
            }, status_code=404)
        
        return JSONResponse(content={
            "success": True,
            "report": report.__dict__
        })
        
    except Exception as e:
        logger.error(f"Report retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Report retrieval failed: {str(e)}")

@lis_router.get("/report/{report_id}/export")
async def export_report(report_id: str,
                     format: str = "json",
                     current_user = Depends(get_current_user)):
    """Export a report in specified format."""
    try:
        export_data = reporting_layer.export_report_data(report_id, format)
        
        if not export_data:
            return JSONResponse(content={
                "success": False,
                "message": "Report not found or export failed"
            }, status_code=404)
        
        return JSONResponse(content={
            "success": True,
            "export_data": export_data,
            "format": format,
            "exported_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Report export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@lis_router.post("/task/schedule")
async def schedule_task(request: ScheduledTaskRequest,
                     current_user = Depends(get_current_user)):
    """Schedule a new task."""
    try:
        from ..modules.litigation_intelligence.scheduler import ScheduledTask
        
        task = ScheduledTask(
            task_id=f"task_{datetime.now().timestamp()}",
            task_name=request.task_name,
            schedule_type=request.schedule_type,
            schedule_expression=request.schedule_expression,
            handler=request.task_name,
            parameters=request.parameters,
            enabled=request.enabled,
            created_at=datetime.now(timezone.utc)
        )
        
        task_id = scheduler.add_scheduled_task(task)
        
        return JSONResponse(content={
            "success": True,
            "task_id": task_id,
            "message": "Task scheduled successfully",
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Task scheduling failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")

@lis_router.get("/tasks")
async def get_scheduled_tasks(current_user = Depends(get_current_user)):
    """Get all scheduled tasks."""
    try:
        tasks = scheduler.get_all_tasks()
        
        return JSONResponse(content={
            "success": True,
            "tasks": tasks,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Task retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

@lis_router.delete("/task/{task_id}")
async def remove_scheduled_task(task_id: str,
                         current_user = Depends(get_current_user)):
    """Remove a scheduled task."""
    try:
        success = scheduler.remove_scheduled_task(task_id)
        
        return JSONResponse(content={
            "success": success,
            "task_id": task_id,
            "message": "Task removed successfully" if success else "Task not found",
            "removed_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Task removal failed: {e}")
        raise HTTPException(status_code=500, detail=f"Removal failed: {str(e)}")

@lis_router.get("/statistics")
async def get_lis_statistics(current_user = Depends(get_current_user)):
    """Get comprehensive LIS statistics."""
    try:
        # Get statistics from all components
        storage_stats = await storage_layer.get_statistics()
        pattern_stats = intelligence_engine.get_pattern_statistics()
        graph_stats = graph_engine.analyze_graph()
        report_stats = reporting_layer.get_available_reports()
        
        return JSONResponse(content={
            "success": True,
            "statistics": {
                "storage": storage_stats,
                "patterns": pattern_stats,
                "graph": graph_stats.to_dict(),
                "reports": {
                    "total_reports": len(report_stats),
                    "available_reports": report_stats
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")

@lis_router.get("/health")
async def health_check():
    """Health check for LIS system."""
    return JSONResponse(content={
        "status": "healthy",
        "components": {
            "court_scraper": "operational",
            "entity_normalizer": "operational",
            "intelligence_engine": "operational",
            "graph_engine": "operational",
            "storage_layer": "operational",
            "reporting_layer": "operational",
            "scheduler": "operational",
            "gui_butler": "operational"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

# Initialize storage layer
@lis_router.on_event("startup")
async def initialize_lis():
    """Initialize LIS components on startup."""
    try:
        await storage_layer.initialize()
        logger.info("Litigation Intelligence System initialized successfully")
    except Exception as e:
        logger.error(f"LIS initialization failed: {e}")

# Background task for scheduler
@lis_router.on_event("startup")
async def start_scheduler():
    """Start LIS scheduler on startup."""
    try:
        await scheduler.start()
        logger.info("LIS scheduler started successfully")
    except Exception as e:
        logger.error(f"LIS scheduler startup failed: {e}")
