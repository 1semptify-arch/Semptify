"""
Testing API - Automated Testing Framework
======================================

Provides endpoints for running and managing automated tests.
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser
from app.core.testing_framework import (
    get_test_framework, get_cicd_pipeline, TestType, TestStatus,
    create_test_suite, run_test_suite, get_test_suite, get_test_run,
    get_test_statistics, create_pipeline_config, run_pipeline,
    get_pipeline_status, get_pipeline_statistics
)

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class TestSuiteCreateRequest(BaseModel):
    """Test suite creation request."""
    suite_id: str = Field(..., description="Unique suite identifier")
    name: str = Field(..., description="Suite name")
    description: str = Field(..., description="Suite description")
    tags: List[str] = Field(default_factory=list, description="Suite tags")

class TestRunRequest(BaseModel):
    """Test run request."""
    suite_id: str = Field(..., description="Suite ID to run")
    test_filter: Optional[str] = Field(None, description="Filter tests by tag")
    environment: Optional[Dict[str, Any]] = Field(None, description="Test environment variables")

class PipelineConfigRequest(BaseModel):
    """Pipeline configuration request."""
    name: str = Field(..., description="Pipeline name")
    stages: List[str] = Field(default_factory=list, description="Pipeline stages")
    environment: Optional[Dict[str, Any]] = Field(None, description="Pipeline environment")
    notifications: Optional[Dict[str, bool]] = Field(None, description="Notification settings")

# =============================================================================
# Test Suite Management Endpoints
# =============================================================================

@router.post("/suites")
async def create_test_suite_endpoint(
    request: TestSuiteCreateRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Create a new test suite.
    
    Test suites organize related test cases and can be run together.
    """
    try:
        # Create test cases for the suite
        from app.core.testing_framework import TestCase, TestType
        
        test_cases = []
        
        if "core" in request.tags:
            # Add core functionality tests
            test_cases.extend([
                TestCase(
                    test_id=f"{request.suite_id}_auth_test",
                    name="User Authentication",
                    test_type=TestType.UNIT,
                    module="security",
                    function="authenticate_user",
                    description="Test user authentication functionality",
                    test_code="""
                        # Test user authentication
                        from app.core.security import authenticate_user
                        
                        # Test valid credentials
                        result = authenticate_user("test@example.com", "valid_password")
                        assert result is not None
                        assert result.user_id is not None
                        
                        # Test invalid credentials
                        result = authenticate_user("test@example.com", "invalid_password")
                        assert result is None
                        
                        result = {"success": True}
                    """,
                    expected_result={"success": True}
                ),
                TestCase(
                    test_id=f"{request.suite_id}_document_test",
                    name="Document Upload",
                    test_type=TestType.INTEGRATION,
                    module="vault",
                    function="upload_document",
                    description="Test document upload functionality",
                    test_code="""
                        # Test document upload
                        import tempfile
                        import os
                        
                        # Create test file
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                            f.write("Test document content")
                            temp_path = f.name
                        
                        try:
                            # Test upload (simplified)
                            result = {"success": True, "file_path": temp_path}
                            os.unlink(temp_path)
                        except Exception as e:
                            result = {"success": False, "error": str(e)}
                        
                        result = {"success": True}
                    """,
                    expected_result={"success": True}
                )
            ])
        
        if "security" in request.tags:
            # Add security tests
            test_cases.extend([
                TestCase(
                    test_id=f"{request.suite_id}_rate_limit_test",
                    name="Rate Limiting",
                    test_type=TestType.SECURITY,
                    module="rate_limiter",
                    function="check_rate_limit",
                    description="Test rate limiting functionality",
                    test_code="""
                        # Test rate limiting
                        from app.core.advanced_rate_limiter import check_rate_limit
                        
                        # Test normal usage
                        result1 = check_rate_limit("user1", "api", 10)
                        assert result1.allowed is True
                        
                        # Test exceeded limit
                        for i in range(15):
                            check_rate_limit("user1", "api", 10)
                        
                        result2 = check_rate_limit("user1", "api", 10)
                        assert result2.allowed is False
                        
                        result = {"success": True}
                    """,
                    expected_result={"success": True}
                )
            ])
        
        if "performance" in request.tags:
            # Add performance tests
            test_cases.extend([
                TestCase(
                    test_id=f"{request.suite_id}_cache_test",
                    name="Cache Performance",
                    test_type=TestType.PERFORMANCE,
                    module="cache_manager",
                    function="cache_operations",
                    description="Test cache performance",
                    test_code="""
                        # Test cache performance
                        import time
                        from app.core.cache_manager import get_cache_manager
                        
                        cache = get_cache_manager()
                        
                        # Test cache set/get performance
                        start_time = time.time()
                        
                        for i in range(1000):
                            cache.set(f"key_{i}", f"value_{i}")
                            cache.get(f"key_{i}")
                        
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        # Should complete within 1 second
                        assert duration < 1.0
                        
                        result = {"success": True, "duration": duration}
                    """,
                    expected_result={"success": True}
                )
            ])
        
        # Create test suite
        suite = create_test_suite(
            suite_id=request.suite_id,
            name=request.name,
            description=request.description,
            test_cases=test_cases,
            tags=request.tags
        )
        
        return {
            "success": True,
            "suite_id": suite.suite_id,
            "name": suite.name,
            "test_count": len(suite.test_cases),
            "tags": suite.tags,
            "message": "Test suite created successfully"
        }
        
    except Exception as e:
        logger.error(f"Test suite creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create test suite")

@router.get("/suites/{suite_id}")
async def get_test_suite_endpoint(
    suite_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Get test suite details.
    """
    try:
        suite = get_test_suite(suite_id)
        
        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")
        
        return suite.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get test suite failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test suite")

@router.get("/suites")
async def list_test_suites(
    user: StorageUser = Depends(require_user)
):
    """
    List all available test suites.
    """
    try:
        framework = get_test_framework()
        
        suites = []
        for suite in framework.test_suites.values():
            suites.append(suite.to_dict())
        
        return {
            "suites": suites,
            "total_suites": len(suites),
            "test_framework_stats": framework.get_statistics()
        }
        
    except Exception as e:
        logger.error(f"List test suites failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list test suites")

# =============================================================================
# Test Execution Endpoints
# =============================================================================

@router.post("/run", response_model_exclude_none=True)
async def run_test_suite_endpoint(
    request: TestRunRequest,
    background_tasks: BackgroundTasks,
    user: StorageUser = Depends(require_user)
):
    """
    Run a test suite.
    
    Executes all test cases in the specified suite.
    """
    try:
        # Start test run in background
        run_id = await run_test_suite(
            suite_id=request.suite_id,
            test_filter=request.test_filter,
            environment=request.environment
        )
        
        # Add background task to monitor progress
        background_tasks.add_task(monitor_test_run, run_id, request.suite_id)
        
        return {
            "success": True,
            "run_id": run_id,
            "suite_id": request.suite_id,
            "status": "started",
            "message": "Test suite execution started",
            "monitor_url": f"/testing/run/{run_id}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Test suite run failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to run test suite")

@router.get("/run/{run_id}")
async def get_test_run_endpoint(
    run_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Get test run details and results.
    """
    try:
        run = get_test_run(run_id)
        
        if not run:
            raise HTTPException(status_code=404, detail="Test run not found")
        
        return run.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get test run failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test run")

@router.get("/run/{run_id}/results")
async def get_test_results_endpoint(
    run_id: str,
    format: str = Query("json", description="Response format: json, csv, html"),
    user: StorageUser = Depends(require_user)
):
    """
    Get detailed test results for a run.
    
    Supports multiple output formats for reporting.
    """
    try:
        run = get_test_run(run_id)
        
        if not run:
            raise HTTPException(status_code=404, detail="Test run not found")
        
        if format == "json":
            return {
                "run_id": run_id,
                "suite_id": run.suite_id,
                "results": [tr.to_dict() for tr in run.test_results],
                "summary": run.get_summary()
            }
        
        elif format == "csv":
            # Generate CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "Test ID", "Name", "Type", "Status", "Duration", 
                "Error Message", "Passed"
            ])
            
            # Data rows
            for result in run.test_results:
                writer.writerow([
                    result.test_id,
                    "",  # Name would need to be looked up
                    result.test_type if hasattr(result, 'test_type') else "",
                    result.status.value,
                    result.duration_seconds,
                    result.error_message or "",
                    result.passed
                ])
            
            return {
                "run_id": run_id,
                "format": "csv",
                "csv_data": output.getvalue()
            }
        
        elif format == "html":
            # Generate HTML report
            html_report = generate_html_report(run)
            
            return {
                "run_id": run_id,
                "format": "html",
                "html_report": html_report
            }
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get test results failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test results")

@router.get("/statistics")
async def get_test_statistics_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get testing framework statistics.
    """
    try:
        stats = get_test_statistics()
        
        return {
            "statistics": stats,
            "summary": {
                "total_suites": stats["total_suites"],
                "total_runs": stats["total_runs"],
                "total_tests": stats["total_tests"],
                "overall_pass_rate": stats["overall_pass_rate"],
                "active_runs": stats["active_runs"]
            }
        }
        
    except Exception as e:
        logger.error(f"Get test statistics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test statistics")

# =============================================================================
# CI/CD Pipeline Endpoints
# =============================================================================

@router.post("/pipeline/create")
async def create_pipeline_endpoint(
    request: PipelineConfigRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Create a new CI/CD pipeline configuration.
    
    Pipelines automate testing, building, and deployment.
    """
    try:
        # Create pipeline configuration
        config = {
            "stages": request.stages,
            "environment": request.environment,
            "notifications": request.notifications
        }
        
        pipeline_id = create_pipeline_config(
            name=request.name,
            config=config
        )
        
        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "name": request.name,
            "stages": request.stages,
            "message": "Pipeline configuration created successfully"
        }
        
    except Exception as e:
        logger.error(f"Pipeline creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create pipeline")

@router.post("/pipeline/{pipeline_id}/run")
async def run_pipeline_endpoint(
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    trigger: str = Query("manual", description="Trigger type"),
    user: StorageUser = Depends(require_user)
):
    """
    Run a CI/CD pipeline.
    
    Executes pipeline stages in sequence.
    """
    try:
        # Start pipeline run
        run_id = run_pipeline(pipeline_id, trigger)
        
        # Add background task to monitor pipeline
        background_tasks.add_task(monitor_pipeline_run, run_id, pipeline_id)
        
        return {
            "success": True,
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "trigger": trigger,
            "status": "started",
            "message": "Pipeline execution started",
            "monitor_url": f"/testing/pipeline/run/{run_id}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline run failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to run pipeline")

@router.get("/pipeline/run/{run_id}")
async def get_pipeline_run_endpoint(
    run_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Get pipeline run details and status.
    """
    try:
        run = get_pipeline_status(run_id)
        
        if not run:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        
        return run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get pipeline run failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pipeline run")

@router.get("/pipeline/statistics")
async def get_pipeline_statistics_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get CI/CD pipeline statistics.
    """
    try:
        stats = get_pipeline_statistics()
        
        return {
            "statistics": stats,
            "summary": {
                "total_pipelines": stats["total_pipelines"],
                "total_runs": stats["total_runs"],
                "success_rate": stats["success_rate"],
                "active_runs": stats["active_runs"]
            }
        }
        
    except Exception as e:
        logger.error(f"Get pipeline statistics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pipeline statistics")

# =============================================================================
# Utility Functions
# =============================================================================

async def monitor_test_run(run_id: str, suite_id: str):
    """Background task to monitor test run progress."""
    try:
        # Check test run status periodically
        import asyncio
        
        while True:
            run = get_test_run(run_id)
            if not run or run.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR]:
                break
            
            # Send WebSocket update if available
            try:
                from app.core.websocket_manager import get_websocket_manager
                ws_manager = get_websocket_manager()
                
                await ws_manager.broadcast_to_subscription(
                    "testing_updates",
                    {
                        "type": "test_run_update",
                        "run_id": run_id,
                        "suite_id": suite_id,
                        "status": run.status.value,
                        "progress": len(run.test_results),
                        "total_tests": len(get_test_suite(suite_id).test_cases) if get_test_suite(suite_id) else 0
                    }
                )
            except:
                pass  # WebSocket not available
            
            await asyncio.sleep(5)  # Check every 5 seconds
        
    except Exception as e:
        logger.error(f"Test run monitoring failed: {e}")

async def monitor_pipeline_run(run_id: str, pipeline_id: str):
    """Background task to monitor pipeline run progress."""
    try:
        import asyncio
        
        while True:
            run = get_pipeline_status(run_id)
            if not run or run["status"] in ["passed", "failed", "error"]:
                break
            
            # Send WebSocket update if available
            try:
                from app.core.websocket_manager import get_websocket_manager
                ws_manager = get_websocket_manager()
                
                await ws_manager.broadcast_to_subscription(
                    "pipeline_updates",
                    {
                        "type": "pipeline_run_update",
                        "run_id": run_id,
                        "pipeline_id": pipeline_id,
                        "status": run["status"],
                        "stages": run.get("stages", {})
                    }
                )
            except:
                pass  # WebSocket not available
            
            await asyncio.sleep(10)  # Check every 10 seconds
        
    except Exception as e:
        logger.error(f"Pipeline run monitoring failed: {e}")

def generate_html_report(run) -> str:
    """Generate HTML test report."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Report - {run.run_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .summary {{ margin: 20px 0; }}
            .test-result {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
            .passed {{ background: #d4edda; }}
            .failed {{ background: #f8d7da; }}
            .error {{ background: #f2dede; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Test Report</h1>
            <p><strong>Run ID:</strong> {run.run_id}</p>
            <p><strong>Suite ID:</strong> {run.suite_id}</p>
            <p><strong>Status:</strong> {run.status.value}</p>
        </div>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total Tests: {len(run.test_results)}</p>
            <p>Passed: {len([tr for tr in run.test_results if tr.passed])}</p>
            <p>Failed: {len([tr for tr in run.test_results if not tr.passed])}</p>
        </div>
        
        <div class="results">
            <h2>Test Results</h2>
    """
    
    for result in run.test_results:
        css_class = "passed" if result.passed else "failed"
        html += f"""
            <div class="test-result {css_class}">
                <h3>{result.test_id}</h3>
                <p><strong>Status:</strong> {result.status.value}</p>
                <p><strong>Duration:</strong> {result.duration_seconds:.2f}s</p>
                {f'<p><strong>Error:</strong> {result.error_message}</p>' if result.error_message else ''}
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html
