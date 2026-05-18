"""
Semptify Development Tools Router
================================

Provides API endpoints for development and analysis tools.
Integrates crawler, auditor, and system analysis capabilities.

Endpoints:
- GET /api/dev/crawl - Run application crawler
- GET /api/dev/crawl/report - Get latest crawl report
- POST /api/dev/analyze - Analyze application structure
- GET /api/dev/health - Development system health
- GET /api/dev/metrics - Development metrics
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.security import require_user, rate_limit_dependency, StorageUser

logger = logging.getLogger(__name__)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class CrawlRequest(BaseModel):
    """Crawl request model"""
    fix_issues: bool = Field(False, description="Automatically fix found issues")
    verbose: bool = Field(False, description="Verbose output")
    target_path: Optional[str] = Field(None, description="Specific path to crawl")

class CrawlResponse(BaseModel):
    """Crawl response model"""
    success: bool = Field(..., description="Crawl success status")
    report_id: str = Field(..., description="Report ID for later retrieval")
    issues_found: int = Field(..., description="Number of issues found")
    issues_fixed: int = Field(..., description="Number of issues fixed")
    duration_seconds: float = Field(..., description="Crawl duration")
    timestamp: str = Field(..., description="Crawl timestamp")

class AnalysisRequest(BaseModel):
    """Analysis request model"""
    analysis_type: str = Field(..., description="Type of analysis to perform")
    target_path: Optional[str] = Field(None, description="Target path for analysis")
    options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")

class AnalysisResponse(BaseModel):
    """Analysis response model"""
    success: bool = Field(..., description="Analysis success status")
    analysis_type: str = Field(..., description="Type of analysis performed")
    results: Dict[str, Any] = Field(..., description="Analysis results")
    timestamp: str = Field(..., description="Analysis timestamp")

class DevHealthResponse(BaseModel):
    """Development health response model"""
    status: str = Field(..., description="Health status")
    tools_available: List[str] = Field(..., description="Available development tools")
    last_crawl: Optional[str] = Field(None, description="Last crawl timestamp")
    system_info: Dict[str, Any] = Field(..., description="System information")

# =============================================================================
# ROUTER SETUP
# =============================================================================

router = APIRouter(
    prefix="/api/dev",
    tags=["Development Tools"],
    responses={404: {"description": "Development tool not found"}},
)

# =============================================================================
# INTERNAL FUNCTIONS
# =============================================================================

async def run_crawler_tool(fix_issues: bool = False, verbose: bool = False, target_path: Optional[str] = None) -> Dict[str, Any]:
    """Run the crawler tool and return results."""
    try:
        # Import crawler module
        import sys
        tools_path = Path(__file__).parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_path))
        
        from app_crawler import AppCrawler
        
        # Initialize crawler
        crawler = AppCrawler(
            base_dir=target_path or Path(__file__).parent.parent.parent,
            verbose=verbose
        )
        
        # Run crawl
        start_time = datetime.now()
        results = await asyncio.get_event_loop().run_in_executor(
            None, crawler.crawl, fix_issues
        )
        end_time = datetime.now()
        
        # Generate report
        report_id = f"crawl_{int(start_time.timestamp())}"
        report_path = tools_path / f"crawl_report_{report_id}.json"
        
        crawl_report = {
            "report_id": report_id,
            "timestamp": start_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "issues_found": len(results.get("issues", [])),
            "issues_fixed": len([i for i in results.get("issues", []) if i.get("fixed", False)]),
            "results": results
        }
        
        # Save report
        with open(report_path, 'w') as f:
            json.dump(crawl_report, f, indent=2)
        
        return crawl_report
        
    except Exception as e:
        logger.error(f"Error running crawler: {e}")
        raise

def get_available_tools() -> List[str]:
    """Get list of available development tools."""
    tools = []
    tools_path = Path(__file__).parent.parent.parent / "tools"
    
    if (tools_path / "app_crawler.py").exists():
        tools.append("crawler")
    if (tools_path / "gui_crawler.py").exists():
        tools.append("gui_crawler")
    
    return tools

def get_system_info() -> Dict[str, Any]:
    """Get system information for development tools."""
    import platform
    import sys
    
    return {
        "platform": platform.platform(),
        "python_version": sys.version,
        "tools_directory": str(Path(__file__).parent.parent.parent / "tools"),
        "app_directory": str(Path(__file__).parent.parent),
    }

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/crawl", response_model=CrawlResponse)
async def run_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: StorageUser = Depends(require_user),
):
    """
    Run the application crawler to find issues and analyze the codebase.
    """
    try:
        # Check if crawler is available
        tools_path = Path(__file__).parent.parent.parent / "tools"
        if not (tools_path / "app_crawler.py").exists():
            raise HTTPException(status_code=503, detail="Crawler tool not available")
        
        # Run crawler
        results = await run_crawler_tool(
            fix_issues=request.fix_issues,
            verbose=request.verbose,
            target_path=request.target_path
        )
        
        logger.info(f"Crawler completed by user {current_user.user_id}: {results['issues_found']} issues found")
        
        return CrawlResponse(
            success=True,
            report_id=results["report_id"],
            issues_found=results["issues_found"],
            issues_fixed=results["issues_fixed"],
            duration_seconds=results["duration_seconds"],
            timestamp=results["timestamp"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running crawl: {e}")
        raise HTTPException(status_code=500, detail="Failed to run crawler")

@router.get("/crawl/report")
async def get_crawl_report(
    report_id: Optional[str] = Query(None, description="Specific report ID"),
    latest: bool = Query(True, description="Get latest report"),
    current_user: StorageUser = Depends(require_user),
):
    """
    Get crawl report results.
    """
    try:
        tools_path = Path(__file__).parent.parent.parent / "tools"
        
        if report_id:
            # Get specific report
            report_path = tools_path / f"crawl_report_{report_id}.json"
            if not report_path.exists():
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        else:
            # Get latest report
            reports = list(tools_path.glob("crawl_report_*.json"))
            if not reports:
                raise HTTPException(status_code=404, detail="No crawl reports found")
            
            report_path = max(reports, key=lambda p: p.stat().st_mtime)
        
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting crawl report: {e}")
        raise HTTPException(status_code=500, detail="Failed to get crawl report")

@router.post("/analyze", response_model=AnalysisResponse)
async def run_analysis(
    request: AnalysisRequest,
    current_user: StorageUser = Depends(require_user),
):
    """
    Run various analysis tools on the application.
    """
    try:
        # Placeholder for different analysis types
        if request.analysis_type == "structure":
            results = await analyze_application_structure(request.target_path)
        elif request.analysis_type == "dependencies":
            results = await analyze_dependencies(request.target_path)
        elif request.analysis_type == "security":
            results = await analyze_security(request.target_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {request.analysis_type}")
        
        logger.info(f"Analysis '{request.analysis_type}' completed by user {current_user.user_id}")
        
        return AnalysisResponse(
            success=True,
            analysis_type=request.analysis_type,
            results=results,
            timestamp=datetime.now().isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to run analysis")

@router.get("/health", response_model=DevHealthResponse)
async def dev_health():
    """
    Get development tools health status.
    """
    try:
        tools = get_available_tools()
        
        # Get latest crawl report timestamp
        tools_path = Path(__file__).parent.parent.parent / "tools"
        reports = list(tools_path.glob("crawl_report_*.json"))
        last_crawl = None
        
        if reports:
            latest_report = max(reports, key=lambda p: p.stat().st_mtime)
            with open(latest_report, 'r') as f:
                report = json.load(f)
            last_crawl = report.get("timestamp")
        
        return DevHealthResponse(
            status="healthy" if tools else "degraded",
            tools_available=tools,
            last_crawl=last_crawl,
            system_info=get_system_info(),
        )
        
    except Exception as e:
        logger.error(f"Error getting dev health: {e}")
        return DevHealthResponse(
            status="unhealthy",
            tools_available=[],
            last_crawl=None,
            system_info={"error": str(e)},
        )

@router.get("/metrics")
async def get_dev_metrics(
    current_user: StorageUser = Depends(require_user),
):
    """
    Get development metrics and statistics.
    """
    try:
        tools_path = Path(__file__).parent.parent.parent / "tools"
        
        # Get crawl statistics
        reports = list(tools_path.glob("crawl_report_*.json"))
        crawl_stats = {
            "total_reports": len(reports),
            "latest_report": None,
            "issues_trend": []
        }
        
        if reports:
            reports.sort(key=lambda p: p.stat().st_mtime)
            latest_report_path = reports[-1]
            
            with open(latest_report_path, 'r') as f:
                latest_report = json.load(f)
            
            crawl_stats["latest_report"] = {
                "timestamp": latest_report.get("timestamp"),
                "issues_found": latest_report.get("issues_found", 0),
                "issues_fixed": latest_report.get("issues_fixed", 0),
            }
            
            # Get trend from last 5 reports
            for report_path in reports[-5:]:
                with open(report_path, 'r') as f:
                    report = json.load(f)
                crawl_stats["issues_trend"].append({
                    "timestamp": report.get("timestamp"),
                    "issues_found": report.get("issues_found", 0),
                })
        
        return {
            "crawl_statistics": crawl_stats,
            "available_tools": get_available_tools(),
            "system_info": get_system_info(),
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error getting dev metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dev metrics")

# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

async def analyze_application_structure(target_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze application structure."""
    base_path = Path(target_path) if target_path else Path(__file__).parent.parent
    
    structure = {
        "directories": [],
        "files_by_type": {},
        "total_files": 0,
        "python_files": 0,
        "html_files": 0,
        "js_files": 0,
        "css_files": 0,
    }
    
    for item in base_path.rglob("*"):
        if item.is_file():
            structure["total_files"] += 1
            suffix = item.suffix.lower()
            
            if suffix == ".py":
                structure["python_files"] += 1
            elif suffix == ".html":
                structure["html_files"] += 1
            elif suffix == ".js":
                structure["js_files"] += 1
            elif suffix == ".css":
                structure["css_files"] += 1
            
            structure["files_by_type"][suffix] = structure["files_by_type"].get(suffix, 0) + 1
        elif item.is_dir() and not item.name.startswith("."):
            structure["directories"].append(str(item.relative_to(base_path)))
    
    return structure

async def analyze_dependencies(target_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze project dependencies."""
    base_path = Path(target_path) if target_path else Path(__file__).parent.parent.parent
    
    dependencies = {
        "requirements_txt": [],
        "pyproject_toml": [],
        "import_analysis": {},
    }
    
    # Parse requirements.txt
    req_file = base_path / "requirements.txt"
    if req_file.exists():
        with open(req_file, 'r') as f:
            dependencies["requirements_txt"] = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    # Parse pyproject.toml
    pyproject_file = base_path / "pyproject.toml"
    if pyproject_file.exists():
        try:
            import tomllib
            with open(pyproject_file, 'rb') as f:
                pyproject = tomllib.load(f)
                dependencies["pyproject_toml"] = list(pyproject.get("project", {}).get("dependencies", []))
        except ImportError:
            # Fallback for older Python versions
            dependencies["pyproject_toml"] = []
    
    return dependencies

async def analyze_security(target_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze security aspects."""
    base_path = Path(target_path) if target_path else Path(__file__).parent.parent
    
    security_issues = []
    
    # Check for common security issues
    for py_file in base_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for potential security issues
            if "eval(" in content:
                security_issues.append({
                    "file": str(py_file.relative_to(base_path)),
                    "issue": "Use of eval() function",
                    "severity": "high"
                })
            
            if "exec(" in content:
                security_issues.append({
                    "file": str(py_file.relative_to(base_path)),
                    "issue": "Use of exec() function",
                    "severity": "high"
                })
                
        except Exception:
            # Skip files that can't be read
            continue
    
    return {
        "security_issues": security_issues,
        "total_issues": len(security_issues),
        "high_severity": len([i for i in security_issues if i.get("severity") == "high"]),
    }
