"""
API Documentation Router - Developer Portal
=========================================

Provides comprehensive API documentation and developer portal.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser
from app.core.api_documentation import (
    get_documentation_generator,
    generate_openapi_spec, generate_postman_collection,
    generate_swagger_ui, generate_redoc_html,
    generate_developer_portal, get_documentation_summary
)

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Documentation Endpoints
# =============================================================================

@router.get("/openapi.json")
async def get_openapi_spec():
    """
    Get OpenAPI 3.0 specification.
    
    Returns the complete API specification in JSON format.
    """
    try:
        spec = generate_openapi_spec()
        return JSONResponse(
            content=spec,
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": "inline; filename=openapi.json"
            }
        )
        
    except Exception as e:
        logger.error(f"OpenAPI spec generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate OpenAPI specification")

@router.get("/postman")
async def get_postman_collection():
    """
    Get Postman collection.
    
    Returns a complete Postman collection for API testing.
    """
    try:
        collection = generate_postman_collection()
        return JSONResponse(
            content=collection,
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": "inline; filename=semtify-api.postman_collection.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Postman collection generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate Postman collection")

@router.get("/swagger", response_class=HTMLResponse)
async def get_swagger_ui():
    """
    Get Swagger UI documentation.
    
    Interactive API documentation with testing capabilities.
    """
    try:
        swagger_html = generate_swagger_ui()
        return HTMLResponse(
            content=swagger_html,
            headers={
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except Exception as e:
        logger.error(f"Swagger UI generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate Swagger UI")

@router.get("/redoc", response_class=HTMLResponse)
async def get_redoc_ui():
    """
    Get ReDoc documentation.
    
    Clean, modern API documentation interface.
    """
    try:
        redoc_html = generate_redoc_html()
        return HTMLResponse(
            content=redoc_html,
            headers={
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except Exception as e:
        logger.error(f"ReDoc UI generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate ReDoc UI")

@router.get("/", response_class=HTMLResponse)
async def get_developer_portal():
    """
    Get developer portal.
    
    Comprehensive developer portal with documentation, examples, and tools.
    """
    try:
        portal_html = generate_developer_portal()
        return HTMLResponse(
            content=portal_html,
            headers={
                "Cache-Control": "public, max-age=1800"  # 30 minutes
            }
        )
        
    except Exception as e:
        logger.error(f"Developer portal generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate developer portal")

# =============================================================================
# API Reference Endpoints
# =============================================================================

@router.get("/reference")
async def get_api_reference():
    """
    Get API reference documentation.
    
    Returns structured API reference for all endpoints.
    """
    try:
        generator = get_documentation_generator()
        
        # Get all modules and endpoints
        reference = {
            "api_version": generator.api_version,
            "base_url": generator.base_url,
            "modules": []
        }
        
        for module in generator.modules.values():
            module_ref = {
                "id": module.module_id,
                "name": module.name,
                "description": module.description,
                "base_path": module.base_path,
                "version": module.version,
                "endpoints": []
            }
            
            for endpoint in module.endpoints:
                endpoint_ref = {
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "summary": endpoint.summary,
                    "description": endpoint.description,
                    "parameters": endpoint.parameters,
                    "request_body": endpoint.request_body,
                    "responses": endpoint.responses,
                    "tags": endpoint.tags,
                    "security": endpoint.security
                }
                module_ref["endpoints"].append(endpoint_ref)
            
            reference["modules"].append(module_ref)
        
        return {
            "reference": reference,
            "statistics": {
                "total_modules": len(reference["modules"]),
                "total_endpoints": sum(len(m["endpoints"]) for m in reference["modules"])
            }
        }
        
    except Exception as e:
        logger.error(f"API reference generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate API reference")

@router.get("/reference/{module_id}")
async def get_module_reference(
    module_id: str
):
    """
    Get specific module reference documentation.
    
    Returns detailed documentation for a specific API module.
    """
    try:
        generator = get_documentation_generator()
        module = generator.modules.get(module_id)
        
        if not module:
            raise HTTPException(status_code=404, detail=f"Module not found: {module_id}")
        
        return {
            "module": module.to_dict(),
            "endpoints": [ep.to_dict() for ep in module.endpoints],
            "statistics": {
                "endpoint_count": len(module.endpoints),
                "tags": list(set(tag for ep in module.endpoints for tag in ep.tags))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Module reference generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate module reference")

# =============================================================================
# Code Examples Endpoints
# =============================================================================

@router.get("/examples")
async def get_code_examples(
    language: Optional[str] = Query(None, description="Filter by programming language"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get code examples for API usage.
    
    Returns code examples in multiple programming languages.
    """
    try:
        generator = get_documentation_generator()
        
        examples = []
        for example in generator.code_examples:
            # Apply filters
            if language and example.language != language:
                continue
            if category and category not in example.description.lower():
                continue
            
            examples.append(example.to_dict())
        
        return {
            "examples": examples,
            "total": len(examples),
            "languages": list(set(ex.language for ex in examples)),
            "categories": [
                "authentication", "documents", "search", "batch_operations",
                "export_import", "security", "testing"
            ],
            "filters": {
                "language": language,
                "category": category
            }
        }
        
    except Exception as e:
        logger.error(f"Code examples retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve code examples")

@router.get("/examples/{example_id}")
async def get_code_example(
    example_id: str
):
    """
    Get specific code example.
    
    Returns detailed code example with explanation.
    """
    try:
        generator = get_documentation_generator()
        
        # Find example by ID
        example = None
        for ex in generator.code_examples:
            if ex.filename == example_id:
                example = ex
                break
        
        if not example:
            raise HTTPException(status_code=404, detail=f"Code example not found: {example_id}")
        
        return example.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code example retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve code example")

# =============================================================================
# SDK and Tools Endpoints
# =============================================================================

@router.get("/sdks")
async def get_sdks():
    """
    Get available SDKs and tools.
    
    Returns information about official SDKs and development tools.
    """
    try:
        sdks = [
            {
                "language": "Python",
                "name": "semptify-python",
                "version": "1.0.0",
                "description": "Official Python SDK for Semptify API",
                "install_command": "pip install semptify-python",
                "repository": "https://github.com/semptify/python-sdk",
                "documentation": "https://docs.semptify.org/python-sdk",
                "status": "stable",
                "features": [
                    "Authentication",
                    "Document Management",
                    "Search",
                    "Batch Operations",
                    "Real-time Notifications"
                ]
            },
            {
                "language": "JavaScript",
                "name": "semptify-js",
                "version": "1.0.0",
                "description": "Official JavaScript SDK for Semptify API",
                "install_command": "npm install semptify-js",
                "repository": "https://github.com/semptify/javascript-sdk",
                "documentation": "https://docs.semptify.org/javascript-sdk",
                "status": "beta",
                "features": [
                    "Authentication",
                    "Document Management",
                    "Search",
                    "Real-time Notifications"
                ]
            },
            {
                "language": "Node.js",
                "name": "semptify-node",
                "version": "1.0.0",
                "description": "Official Node.js SDK for Semptify API",
                "install_command": "npm install semptify-node",
                "repository": "https://github.com/semptify/node-sdk",
                "documentation": "https://docs.semptify.org/node-sdk",
                "status": "alpha",
                "features": [
                    "Authentication",
                    "Document Management",
                    "Search",
                    "Batch Operations"
                ]
            }
        ]
        
        tools = [
            {
                "name": "semptify-cli",
                "type": "Command Line Interface",
                "description": "Official CLI tool for Semptify API",
                "install_command": "npm install -g semptify-cli",
                "repository": "https://github.com/semptify/cli",
                "status": "stable",
                "features": [
                    "Authentication",
                    "Document Upload/Download",
                    "Search",
                    "Batch Operations",
                    "Configuration Management"
                ]
            },
            {
                "name": "semptify-vscode",
                "type": "VS Code Extension",
                "description": "VS Code extension for Semptify development",
                "marketplace_url": "https://marketplace.visualstudio.com/items?itemName=semptify.vscode",
                "status": "beta",
                "features": [
                    "API Documentation",
                    "Code Completion",
                    "Request Testing",
                    "Authentication Helper"
                ]
            }
        ]
        
        return {
            "sdks": sdks,
            "tools": tools,
            "statistics": {
                "total_sdks": len(sdks),
                "total_tools": len(tools),
                "stable_releases": len([sdk for sdk in sdks if sdk["status"] == "stable"]),
                "beta_releases": len([sdk for sdk in sdks if sdk["status"] == "beta"]),
                "alpha_releases": len([sdk for sdk in sdks if sdk["status"] == "alpha"])
            }
        }
        
    except Exception as e:
        logger.error(f"SDKs retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve SDKs")

# =============================================================================
# Support and Resources Endpoints
# =============================================================================

@router.get("/support")
async def get_support_resources():
    """
    Get support resources and links.
    
    Returns comprehensive support resources for developers.
    """
    try:
        resources = {
            "documentation": {
                "api_reference": "https://docs.semptify.org/api",
                "guides": "https://docs.semptify.org/guides",
                "tutorials": "https://docs.semptify.org/tutorials",
                "faq": "https://docs.semptify.org/faq"
            },
            "community": {
                "github": "https://github.com/semptify/api",
                "discord": "https://discord.gg/semptify",
                "stackoverflow": "https://stackoverflow.com/questions/tagged/semptify",
                "reddit": "https://reddit.com/r/semptify"
            },
            "support": {
                "email": "api-support@semptify.org",
                "helpdesk": "https://support.semptify.org",
                "status_page": "https://status.semptify.org"
            },
            "tools": {
                "api_testing": "https://api-test.semptify.org",
                "webhooks": "https://webhooks.semptify.org",
                "monitoring": "https://monitoring.semptify.org"
            },
            "legal": {
                "terms_of_service": "https://semptify.org/terms",
                "privacy_policy": "https://semptify.org/privacy",
                "api_terms": "https://semptify.org/api-terms",
                "rate_limits": "https://semptify.org/rate-limits"
            }
        }
        
        return resources
        
    except Exception as e:
        logger.error(f"Support resources retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve support resources")

@router.get("/changelog")
async def get_changelog():
    """
    Get API changelog and version history.
    
    Returns detailed changelog for API versions.
    """
    try:
        changelog = [
            {
                "version": "1.2.0",
                "release_date": "2024-04-17",
                "status": "stable",
                "description": "Major update with advanced features",
                "changes": [
                    {
                        "type": "added",
                        "category": "security",
                        "description": "Two-factor authentication (2FA) support",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "performance",
                        "description": "Advanced caching and rate limiting",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "search",
                        "description": "Full-text search with BM25 scoring",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "documents",
                        "description": "Document preview and thumbnail generation",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "batch",
                        "description": "Batch operations for document management",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "testing",
                        "description": "Automated testing and CI/CD pipeline",
                        "breaking": False
                    }
                ]
            },
            {
                "version": "1.1.0",
                "release_date": "2024-03-15",
                "status": "stable",
                "description": "Enhanced search and notifications",
                "changes": [
                    {
                        "type": "added",
                        "category": "search",
                        "description": "Advanced search with indexing",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "notifications",
                        "description": "Real-time WebSocket notifications",
                        "breaking": False
                    },
                    {
                        "type": "improved",
                        "category": "performance",
                        "description": "Database connection pooling and caching",
                        "breaking": False
                    }
                ]
            },
            {
                "version": "1.0.0",
                "release_date": "2024-02-01",
                "status": "stable",
                "description": "Initial release",
                "changes": [
                    {
                        "type": "added",
                        "category": "core",
                        "description": "Basic API functionality",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "authentication",
                        "description": "User authentication and authorization",
                        "breaking": False
                    },
                    {
                        "type": "added",
                        "category": "documents",
                        "description": "Document management endpoints",
                        "breaking": False
                    }
                ]
            }
        ]
        
        return {
            "changelog": changelog,
            "current_version": "1.2.0",
            "statistics": {
                "total_versions": len(changelog),
                "stable_versions": len([v for v in changelog if v["status"] == "stable"]),
                "breaking_changes": len([
                    change for version in changelog
                    for change in version["changes"]
                    if change["breaking"]
                ])
            }
        }
        
    except Exception as e:
        logger.error(f"Changelog retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve changelog")

# =============================================================================
# Statistics and Monitoring Endpoints
# =============================================================================

@router.get("/statistics")
async def get_documentation_statistics():
    """
    Get documentation statistics and usage metrics.
    
    Returns statistics about API documentation and developer portal usage.
    """
    try:
        summary = get_documentation_summary()
        
        # Add usage statistics (would be tracked in production)
        usage_stats = {
            "api_spec_downloads": 1250,  # Example data
            "postman_downloads": 890,
            "swagger_ui_visits": 3420,
            "redoc_visits": 2150,
            "developer_portal_visits": 1890,
            "code_example_views": 1560
        }
        
        return {
            "documentation": summary,
            "usage": usage_stats,
            "trends": {
                "most_viewed_modules": ["documents", "authentication", "search"],
                "most_downloaded_sdks": ["python", "javascript"],
                "popular_examples": ["authentication", "document_upload", "search"]
            }
        }
        
    except Exception as e:
        logger.error(f"Documentation statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve documentation statistics")
