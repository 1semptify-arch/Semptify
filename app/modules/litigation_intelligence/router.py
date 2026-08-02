"""
Litigation Intelligence System Router - Justice-Grade Legal Intelligence API
=====================================================================

FastAPI router for Litigation Intelligence System (LIS).
Provides endpoints for court scraping, entity resolution, intelligence analysis,
graph visualization, storage, reporting, and scheduling.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.core.utc import utc_now

from .court_scraper import create_court_scraper
from .entity_normalizer import create_entity_normalizer
from .graph_engine import create_graph_engine
from .gui_butler import create_gui_butler
from .intelligence_engine import create_intelligence_engine
from .reporting_layer import create_reporting_layer
from .scheduler import create_litigation_scheduler
from .storage_layer import create_storage_layer

logger = logging.getLogger(__name__)

# Initialize LIS components
lis_router = APIRouter(prefix="/api/litigation-intelligence", tags=["Litigation Intelligence"])


# Pydantic Models
class CourtScrapingRequest(BaseModel):
    """Request for court scraping operations."""

    case_number: str | None = Field(None, description="Case number to search")
    attorney_name: str | None = Field(None, description="Attorney name to search")
    date_range: str | None = Field(None, description="Date range for search")
    court_system: str = Field(..., description="Court system to scrape (mncis, efilemn)")


class EntityNormalizationRequest(BaseModel):
    """Request for entity normalization."""

    entity_name: str = Field(..., description="Entity name to normalize")
    context: str = Field("general", description="Context for normalization")


class CaseAnalysisRequest(BaseModel):
    """Request for case intelligence analysis."""

    case_data: dict[str, Any] = Field(..., description="Case data to analyze")
    analysis_options: dict[str, Any] | None = Field(None, description="Analysis options")


class GraphVisualizationRequest(BaseModel):
    """Request for graph visualization."""

    entities: list[dict[str, Any]] = Field(..., description="Entities to include in graph")
    relationship_data: list[dict[str, Any]] | None = Field(None, description="Relationship data between entities")
    visualization_options: dict[str, Any] | None = Field(None, description="Visualization options")


class ReportGenerationRequest(BaseModel):
    """Request for report generation."""

    report_type: str = Field(..., description="Type of report to generate")
    time_period: str = Field("30_days", description="Time period for report")
    filters: dict[str, Any] | None = Field(None, description="Filters for report")
    export_format: str = Field("json", description="Export format (json, csv, pdf)")


class NormalizeEntitiesRequest(BaseModel):
    """Request for normalizing multiple entities."""

    entities: list[Any] = Field(..., description="List of entities to normalize")
    context: str = Field("general", description="Context for normalization")


class ScheduledTaskRequest(BaseModel):
    """Request for scheduled task management."""

    task_name: str = Field(..., description="Task name")
    schedule_type: str = Field(..., description="Schedule type (cron, interval, once)")
    schedule_expression: str = Field(..., description="Schedule expression")
    parameters: dict[str, Any] = Field(..., description="Task parameters")
    enabled: bool = Field(True, description="Whether task is enabled")


# Initialize LIS components
court_scraper = create_court_scraper()
entity_normalizer = create_entity_normalizer()
intelligence_engine = create_intelligence_engine()
graph_engine = create_graph_engine()
storage_layer = create_storage_layer("postgresql://user:password@localhost/semptify_lis")
reporting_layer = create_reporting_layer(storage_layer)
gui_butler = create_gui_butler()
scheduler = create_litigation_scheduler()


@lis_router.post("/scrape/court")
async def scrape_court_system(request: CourtScrapingRequest, current_user=Depends(get_current_user)):
    """Scrape court system for case data."""
    try:
        if request.court_system == "mncis":
            cases = await court_scraper.scrape_mncis_cases(
                case_number=request.case_number, attorney_name=request.attorney_name, date_range=request.date_range
            )
        elif request.court_system == "efilemn":
            cases = await court_scraper.scrape_efilemn_cases(
                case_number=request.case_number, party_name=request.attorney_name
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported court system")

        return JSONResponse(
            content={
                "success": True,
                "cases": cases,
                "court_system": request.court_system,
                "scraped_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Court scraping failed: {e}")
        logger.exception("Scraping failed")
        raise HTTPException(status_code=500, detail="Scraping failed")


@lis_router.post("/scrape/filings/{case_number}")
async def scrape_case_filings(case_number: str, current_user=Depends(get_current_user)):
    """Scrape specific case filings."""
    try:
        filings = await court_scraper.scrape_efilemn_filings(case_number)

        return JSONResponse(
            content={
                "success": True,
                "case_number": case_number,
                "filings": filings,
                "scraped_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Filing scraping failed: {e}")
        logger.exception("Scraping failed")
        raise HTTPException(status_code=500, detail="Scraping failed")


@lis_router.post("/normalize/entity")
async def normalize_entity(request: EntityNormalizationRequest, current_user=Depends(get_current_user)):
    """Normalize an entity name."""
    try:
        resolution = entity_normalizer.normalize_entity(request.entity_name, request.context)

        return JSONResponse(
            content={"success": True, "resolution": resolution.to_dict(), "normalized_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Entity normalization failed: {e}")
        logger.exception("Normalization failed")
        raise HTTPException(status_code=500, detail="Normalization failed")


@lis_router.post("/normalize/entities")
async def normalize_entities(request: NormalizeEntitiesRequest, current_user=Depends(get_current_user)):
    """Normalize multiple entities."""
    try:
        resolutions = entity_normalizer.resolve_entities(request.entities, request.context)

        return JSONResponse(
            content={
                "success": True,
                "resolutions": [r.to_dict() for r in resolutions],
                "normalized_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Entity normalization failed: {e}")
        logger.exception("Normalization failed")
        raise HTTPException(status_code=500, detail="Normalization failed")


@lis_router.post("/analyze/case")
async def analyze_case_intelligence(request: CaseAnalysisRequest, current_user=Depends(get_current_user)):
    """Analyze case for intelligence patterns."""
    try:
        report = await intelligence_engine.analyze_case(request.case_data)

        return JSONResponse(
            content={"success": True, "intelligence_report": report.__dict__, "analyzed_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Case analysis failed: {e}")
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="Analysis failed")


@lis_router.get("/intelligence/{case_id}")
async def get_case_intelligence(case_id: str, current_user=Depends(get_current_user)):
    """Get stored intelligence report for a case."""
    try:
        report = intelligence_engine.get_case_intelligence(case_id)

        if not report:
            return JSONResponse(content={"success": False, "message": "Intelligence report not found"}, status_code=404)

        return JSONResponse(content={"success": True, "intelligence_report": report.__dict__})

    except Exception as e:
        logger.error(f"Intelligence retrieval failed: {e}")
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=500, detail="Retrieval failed")


@lis_router.post("/graph/build")
async def build_entity_graph(request: GraphVisualizationRequest, current_user=Depends(get_current_user)):
    """Build an entity relationship graph from the supplied entities and relationships."""
    try:
        engine = create_graph_engine()
        engine.build_from_entities(request.entities)
        for rel in request.relationship_data or []:
            if isinstance(rel, dict):
                engine.add_relationship(
                    rel.get("source", ""),
                    rel.get("target", ""),
                    rel.get("type", "related_to"),
                    rel.get("weight", 1.0),
                    rel.get("attributes", {}),
                )
        return JSONResponse(content={"success": True, "graph": engine.export_graph_data()})
    except Exception as exc:
        logger.error("Graph build failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Graph build failed") from exc


@lis_router.post("/graph/visualize")
async def generate_graph_visualization(request: GraphVisualizationRequest, current_user=Depends(get_current_user)):
    """Generate a graph visualization from the supplied entities and relationships."""
    try:
        engine = create_graph_engine()
        engine.build_from_entities(request.entities)
        for rel in request.relationship_data or []:
            if isinstance(rel, dict):
                engine.add_relationship(
                    rel.get("source", ""),
                    rel.get("target", ""),
                    rel.get("type", "related_to"),
                    rel.get("weight", 1.0),
                    rel.get("attributes", {}),
                )
        fmt = (request.visualization_options or {}).get("format", "png")
        return JSONResponse(content={"success": True, "visualization": engine.generate_visualization(fmt)})
    except Exception as exc:
        logger.error("Graph visualization failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Graph visualization failed") from exc


@lis_router.post("/graph/path/{source_entity}/{target_entity}")
async def find_shortest_path(
    source_entity: str,
    target_entity: str,
    request: GraphVisualizationRequest | None = None,
    current_user=Depends(get_current_user),
):
    """Find the shortest path between two entities in a graph.

    Optionally supply `entities` and `relationship_data` in the request body
    to build a fresh graph for the search. If no body is supplied, the
    module-level graph engine is used.
    """
    try:
        engine = graph_engine
        if request and request.entities:
            engine = create_graph_engine()
            engine.build_from_entities(request.entities)
            for rel in request.relationship_data or []:
                if isinstance(rel, dict):
                    engine.add_relationship(
                        rel.get("source", ""),
                        rel.get("target", ""),
                        rel.get("type", "related_to"),
                        rel.get("weight", 1.0),
                        rel.get("attributes", {}),
                    )

        path = engine.find_shortest_path(source_entity, target_entity)
        if path is None:
            return JSONResponse(
                content={"success": True, "path": [], "message": "No path found"},
                status_code=200,
            )
        return JSONResponse(content={"success": True, "path": path})
    except Exception as exc:
        logger.error("Shortest path search failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Shortest path search failed") from exc


@lis_router.post("/report/generate")
async def generate_report(request: ReportGenerationRequest, current_user=Depends(get_current_user)):
    """Generate litigation intelligence report."""
    try:
        if request.report_type == "case_summary":
            report = await reporting_layer.generate_case_summary_report(request.time_period, request.filters)
        elif request.report_type == "entity_analysis":
            report = await reporting_layer.generate_entity_analysis_report(
                request.time_period, request.filters.get("entity_type") if request.filters else None
            )
        elif request.report_type == "pattern_trends":
            report = await reporting_layer.generate_pattern_trends_report(request.time_period)
        elif request.report_type == "success_metrics":
            report = await reporting_layer.generate_success_metrics_report(request.time_period)
        else:
            raise HTTPException(status_code=400, detail="Unsupported report type")

        return JSONResponse(
            content={"success": True, "report": report.to_dict(), "generated_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail="Report generation failed")


@lis_router.get("/report/{report_id}")
async def get_report(report_id: str, current_user=Depends(get_current_user)):
    """Get a generated report."""
    try:
        report = reporting_layer.get_report(report_id)

        if not report:
            return JSONResponse(content={"success": False, "message": "Report not found"}, status_code=404)

        return JSONResponse(content={"success": True, "report": report.to_dict()})

    except Exception as e:
        logger.error(f"Report retrieval failed: {e}")
        logger.exception("Report retrieval failed")
        raise HTTPException(status_code=500, detail="Report retrieval failed")


@lis_router.get("/report/{report_id}/export")
async def export_report(report_id: str, format: str = "json", current_user=Depends(get_current_user)):
    """Export a report in specified format."""
    try:
        export_data = reporting_layer.export_report_data(report_id, format)

        if not export_data:
            return JSONResponse(
                content={"success": False, "message": "Report not found or export failed"}, status_code=404
            )

        return JSONResponse(
            content={
                "success": True,
                "export_data": export_data,
                "format": format,
                "exported_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Report export failed: {e}")
        logger.exception("Export failed")
        raise HTTPException(status_code=500, detail="Export failed")


@lis_router.post("/task/schedule")
async def schedule_task(request: ScheduledTaskRequest, current_user=Depends(get_current_user)):
    """Schedule a new task."""
    try:
        from ..modules.litigation_intelligence.scheduler import ScheduledTask

        task = ScheduledTask(
            task_id=f"task_{utc_now().timestamp()}",
            task_name=request.task_name,
            schedule_type=request.schedule_type,
            schedule_expression=request.schedule_expression,
            handler=request.task_name,
            parameters=request.parameters,
            enabled=request.enabled,
            created_at=utc_now(),
        )

        task_id = scheduler.add_scheduled_task(task)

        return JSONResponse(
            content={
                "success": True,
                "task_id": task_id,
                "message": "Task scheduled successfully",
                "scheduled_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Task scheduling failed: {e}")
        logger.exception("Scheduling failed")
        raise HTTPException(status_code=500, detail="Scheduling failed")


@lis_router.get("/tasks")
async def get_scheduled_tasks(current_user=Depends(get_current_user)):
    """Get all scheduled tasks."""
    try:
        tasks = scheduler.get_all_tasks()

        return JSONResponse(content={"success": True, "tasks": tasks, "retrieved_at": utc_now().isoformat()})

    except Exception as e:
        logger.error(f"Task retrieval failed: {e}")
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=500, detail="Retrieval failed")


@lis_router.delete("/task/{task_id}")
async def remove_scheduled_task(task_id: str, current_user=Depends(get_current_user)):
    """Remove a scheduled task."""
    try:
        success = scheduler.remove_scheduled_task(task_id)

        return JSONResponse(
            content={
                "success": success,
                "task_id": task_id,
                "message": "Task removed successfully" if success else "Task not found",
                "removed_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Task removal failed: {e}")
        logger.exception("Removal failed")
        raise HTTPException(status_code=500, detail="Removal failed")


@lis_router.get("/statistics")
async def get_lis_statistics(current_user=Depends(get_current_user)):
    """Get comprehensive LIS statistics."""
    try:
        # Get statistics from all components
        storage_stats = await storage_layer.get_statistics()
        pattern_stats = intelligence_engine.get_pattern_statistics()
        graph_stats = graph_engine.analyze_graph()
        report_stats = reporting_layer.get_available_reports()

        return JSONResponse(
            content={
                "success": True,
                "statistics": {
                    "storage": storage_stats,
                    "patterns": pattern_stats,
                    "graph": graph_stats,
                    "reports": {"total_reports": len(report_stats), "available_reports": report_stats},
                    "generated_at": utc_now().isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        logger.exception("Statistics failed")
        raise HTTPException(status_code=500, detail="Statistics failed")


@lis_router.get("/health")
async def health_check():
    """Health check for LIS system."""
    return JSONResponse(
        content={
            "status": "healthy",
            "components": {
                "court_scraper": "operational",
                "entity_normalizer": "operational",
                "intelligence_engine": "operational",
                "graph_engine": "operational",
                "storage_layer": "operational",
                "reporting_layer": "operational",
                "scheduler": "operational",
                "gui_butler": "operational",
            },
            "timestamp": utc_now().isoformat(),
        }
    )


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
