"""
API Documentation Generator - Developer Portal
===========================================

Generates comprehensive API documentation and developer portal.
"""

import logging
from app.core.utc import utc_now
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import inspect
import asyncio

logger = logging.getLogger(__name__)

class DocumentationType(Enum):
    """Documentation types."""
    OPENAPI = "openapi"
    POSTMAN = "postman"
    SWAGGER = "swagger"
    REDOC = "redoc"

class APIEndpoint:
    """API endpoint documentation."""
    def __init__(self, path: str, method: str, summary: str, 
                 description: str, parameters: List[Dict[str, Any]] = None,
                 request_body: Dict[str, Any] = None, responses: Dict[str, Any] = None,
                 tags: List[str] = None, security: List[str] = None):
        self.path = path
        self.method = method.upper()
        self.summary = summary
        self.description = description
        self.parameters = parameters or []
        self.request_body = request_body
        self.responses = responses or {}
        self.tags = tags or []
        self.security = security or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "summary": self.summary,
            "description": self.description,
            "parameters": self.parameters,
            "request_body": self.request_body,
            "responses": self.responses,
            "tags": self.tags,
            "security": self.security
        }

@dataclass
class APIModule:
    """API module documentation."""
    module_id: str
    name: str
    description: str
    endpoints: List[APIEndpoint]
    version: str
    base_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CodeExample:
    """Code example for API usage."""
    language: str
    code: str
    description: str
    filename: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class APIDocumentationGenerator:
    """Generates comprehensive API documentation."""
    
    def __init__(self):
        self.modules: Dict[str, APIModule] = {}
        self.code_examples: List[CodeExample] = []
        
        # Documentation settings
        self.api_version = "v1"
        self.base_url = "https://api.semptify.org"
        self.contact_info = {
            "name": "Semptify API Team",
            "email": "api@semptify.org",
            "url": "https://semptify.org/support"
        }
        self.license_info = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
    
    def register_module(self, module: APIModule):
        """Register an API module for documentation."""
        self.modules[module.module_id] = module
        logger.info(f"Registered API module {module.module_id}")
    
    def add_code_example(self, example: CodeExample):
        """Add a code example."""
        self.code_examples.append(example)
    
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification."""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Semptify API",
                "description": "Housing Rights Platform API",
                "version": self.api_version,
                "contact": self.contact_info,
                "license": self.license_info
            },
            "servers": [
                {
                    "url": self.base_url,
                    "description": "Production server"
                },
                {
                    "url": "https://api-staging.semptify.org",
                    "description": "Staging server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {}
            }
        }
        
        # Add all endpoints to paths
        for module in self.modules.values():
            for endpoint in module.endpoints:
                if endpoint.path not in spec["paths"]:
                    spec["paths"][endpoint.path] = {}
                
                spec["paths"][endpoint.path][endpoint.method.lower()] = {
                    "summary": endpoint.summary,
                    "description": endpoint.description,
                    "tags": endpoint.tags,
                    "parameters": endpoint.parameters,
                    "requestBody": endpoint.request_body,
                    "responses": endpoint.responses,
                    "security": endpoint.security
                }
        
        # Add common schemas
        spec["components"]["schemas"] = {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "email": {"type": "string", "format": "email"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "subscription_tier": {"type": "string", "enum": ["free", "basic", "premium", "enterprise"]}
                }
            },
            "Document": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "filename": {"type": "string"},
                    "document_type": {"type": "string"},
                    "file_size": {"type": "integer"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                }
            },
            "Error": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "message": {"type": "string"},
                    "status_code": {"type": "integer"}
                }
            }
        }
        
        # Add security schemes
        spec["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "OAuth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "/oauth/authorize",
                        "tokenUrl": "/oauth/token",
                        "scopes": {
                            "read": "Read access",
                            "write": "Write access",
                            "admin": "Admin access"
                        }
                    }
                }
            }
        }
        
        return spec
    
    def generate_postman_collection(self) -> Dict[str, Any]:
        """Generate Postman collection."""
        collection = {
            "info": {
                "name": "Semptify API",
                "description": "Complete API collection for Semptify",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": []
        }
        
        # Group endpoints by module
        for module in self.modules.values():
            module_item = {
                "name": module.name,
                "description": module.description,
                "item": []
            }
            
            for endpoint in module.endpoints:
                endpoint_item = {
                    "name": endpoint.summary,
                    "request": {
                        "method": endpoint.method,
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            },
                            {
                                "key": "Authorization",
                                "value": "Bearer {{token}}"
                            }
                        ],
                        "url": {
                            "raw": f"{{base_url}}{module.base_path}{endpoint.path}",
                            "host": ["{{base_url}}"]
                        }
                    }
                }
                
                # Add request body if present
                if endpoint.request_body:
                    endpoint_item["request"]["body"] = {
                        "mode": "raw",
                        "raw": json.dumps(endpoint.request_body.get("example", {}), indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }
                
                # Add response examples
                if endpoint.responses:
                    endpoint_item["response"] = []
                    for status_code, response in endpoint.responses.items():
                        response_item = {
                            "name": f"{status_code} {response.get('description', '')}",
                            "originalRequest": {
                                "method": endpoint.method,
                                "url": {
                                    "raw": f"{{base_url}}{module.base_path}{endpoint.path}"
                                }
                            },
                            "code": int(status_code),
                            "status": "OK" if 200 <= int(status_code) < 300 else "Error"
                        }
                        
                        if "example" in response:
                            response_item["body"] = json.dumps(response["example"], indent=2)
                        
                        endpoint_item["response"].append(response_item)
                
                module_item["item"].append(endpoint_item)
            
            collection["item"].append(module_item)
        
        return collection
    
    def generate_swagger_ui(self) -> str:
        """Generate Swagger UI HTML."""
        openapi_spec = self.generate_openapi_spec()
        
        swagger_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Semptify API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css" />
            <style>
                html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
                *, *:before, *:after {{ box-sizing: inherit; }}
                body {{ margin: 0; background: #fafafa; }}
                .swagger-ui .topbar {{ background-color: #1b1b1b; }}
                .swagger-ui .topbar .download-url-wrapper {{ display: none; }}
            </style>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
            <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-standalone-preset.js"></script>
            <script>
                window.onload = function() {{
                    const ui = SwaggerUIBundle({{
                        url: '/docs/openapi.json',
                        dom_id: '#swagger-ui',
                        deepLinking: true,
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIStandalonePreset
                        ],
                        plugins: [
                            SwaggerUIBundle.plugins.DownloadUrl
                        ],
                        layout: "StandaloneLayout"
                    }});
                }};
            </script>
        </body>
        </html>
        """
        
        return swagger_html
    
    def generate_redoc_html(self) -> str:
        """Generate ReDoc HTML."""
        openapi_spec = self.generate_openapi_spec()
        
        redoc_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Semptify API Documentation</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
                body {{ margin: 0; padding: 0; font-family: sans-serif; }}
                .redoc-wrap {{ background: #fafafa; }}
                .api-content {{ max-width: 960px; margin: 0 auto; padding: 40px 0; }}
                .api-info {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="redoc-wrap">
                <div class="api-content">
                    <div class="api-info">
                        <h1>Semptify API Documentation</h1>
                        <p>Complete API documentation for the Semptify housing rights platform</p>
                        <p><strong>Version:</strong> {self.api_version}</p>
                        <p><strong>Base URL:</strong> {self.base_url}</p>
                    </div>
                    <redoc spec-url="/docs/openapi.json"></redoc>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """
        
        return redoc_html
    
    def generate_developer_portal(self) -> str:
        """Generate extensive interactive developer portal HTML with admin guide."""
        modules_list = []
        for module in self.modules.values():
            modules_list.append({
                "id": module.module_id,
                "name": module.name,
                "description": module.description,
                "base_path": module.base_path,
                "endpoint_count": len(module.endpoints),
                "version": module.version
            })
        
        code_examples_list = []
        for example in self.code_examples:
            code_examples_list.append(example.to_dict())
        
        portal_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Semptify API Developer Portal</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #1a202c; min-height: 100vh; }}
                .container {{ max-width: 1400px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); margin-bottom: 30px; position: relative; overflow: hidden; }}
                .header::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #667eea, #764ba2); }}
                .header h1 {{ font-size: 3rem; font-weight: 800; color: #1e293b; margin-bottom: 15px; letter-spacing: -0.5px; }}
                .header p {{ font-size: 1.2rem; color: #64748b; line-height: 1.7; margin-bottom: 20px; }}
                .header .meta {{ display: flex; gap: 20px; font-size: 0.9rem; color: #94a3b8; }}
                .header .meta span {{ display: flex; align-items: center; gap: 5px; }}
                .nav {{ display: flex; gap: 8px; margin-bottom: 30px; flex-wrap: wrap; background: rgba(255,255,255,0.1); padding: 8px; border-radius: 12px; backdrop-filter: blur(10px); }}
                .nav-item {{ background: white; padding: 14px 24px; border-radius: 10px; text-decoration: none; color: #1e293b; font-weight: 600; border: 2px solid transparent; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; position: relative; overflow: hidden; }}
                .nav-item::before {{ content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.1), transparent); transition: left 0.5s; }}
                .nav-item:hover::before {{ left: 100%; }}
                .nav-item:hover {{ border-color: #667eea; transform: translateY(-3px) scale(1.02); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3); }}
                .nav-item.active {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: transparent; box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }}
                .content-section {{ display: none; animation: fadeIn 0.5s ease-out; }}
                .content-section.active {{ display: block; }}
                @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                .card {{ background: white; padding: 35px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); margin-bottom: 25px; transition: all 0.3s ease; position: relative; overflow: hidden; }}
                .card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #667eea, #764ba2); opacity: 0; transition: opacity 0.3s; }}
                .card:hover::before {{ opacity: 1; }}
                .card:hover {{ transform: translateY(-5px); box-shadow: 0 20px 60px rgba(0,0,0,0.15); }}
                .card h2 {{ font-size: 1.8rem; font-weight: 700; color: #1e293b; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }}
                .card h2::before {{ content: '📖'; font-size: 1.5rem; }}
                .card h3 {{ font-size: 1.3rem; font-weight: 600; color: #334155; margin: 25px 0 15px 0; }}
                .card p {{ color: #475569; line-height: 1.8; margin-bottom: 15px; }}
                .card code {{ background: #f1f5f9; padding: 3px 8px; border-radius: 4px; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em; color: #e11d48; }}
                .card pre {{ background: #1e293b; color: #e2e8f0; padding: 20px; border-radius: 10px; overflow-x: auto; margin: 20px 0; }}
                .card pre code {{ background: none; color: inherit; padding: 0; }}
                .card ul {{ padding-left: 25px; margin: 15px 0; }}
                .card li {{ color: #475569; line-height: 1.8; margin-bottom: 10px; }}
                .card li::marker {{ color: #667eea; }}
                .card .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .card .warning::before {{ content: '⚠️ '; font-weight: bold; }}
                .card .info {{ background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .card .info::before {{ content: 'ℹ️ '; font-weight: bold; }}
                .card .success {{ background: #d1fae5; border-left: 4px solid #10b981; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .card .success::before {{ content: '✅ '; font-weight: bold; }}
                .module-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
                .module-item {{ background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); padding: 25px; border-radius: 12px; border-left: 5px solid #667eea; transition: all 0.3s ease; cursor: pointer; position: relative; overflow: hidden; }}
                .module-item::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)); opacity: 0; transition: opacity 0.3s; }}
                .module-item:hover::before {{ opacity: 1; }}
                .module-item:hover {{ transform: translateX(10px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2); }}
                .module-name {{ font-weight: 700; color: #1e293b; margin-bottom: 8px; font-size: 1.2rem; }}
                .module-path {{ color: #64748b; font-family: 'Monaco', 'Menlo', monospace; background: #e5e7eb; padding: 6px 12px; border-radius: 6px; display: inline-block; margin-bottom: 12px; font-size: 0.85rem; }}
                .module-stats {{ display: flex; gap: 20px; font-size: 0.9rem; color: #64748b; margin-bottom: 12px; }}
                .stat {{ display: flex; align-items: center; gap: 6px; background: white; padding: 5px 10px; border-radius: 20px; }}
                .code-examples {{ display: grid; gap: 25px; }}
                .code-example {{ background: #1e293b; color: white; padding: 30px; border-radius: 12px; margin-bottom: 25px; position: relative; overflow: hidden; }}
                .code-example::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #667eea, #764ba2); }}
                .code-example h3 {{ margin-bottom: 20px; color: #e2e8f0; display: flex; align-items: center; gap: 10px; }}
                .code-example h3::before {{ content: '💻'; }}
                .code-block {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 20px; overflow-x: auto; }}
                .code-block pre {{ margin: 0; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9rem; line-height: 1.6; color: #e2e8f0; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 600; transition: all 0.3s ease; cursor: pointer; border: none; position: relative; overflow: hidden; }}
                .btn::before {{ content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent); transition: left 0.5s; }}
                .btn:hover::before {{ left: 100%; }}
                .btn:hover {{ transform: translateY(-3px) scale(1.05); box-shadow: 0 15px 40px rgba(102, 126, 234, 0.4); }}
                .btn-secondary {{ background: linear-gradient(135deg, #64748b 0%, #475569 100%); }}
                .btn-secondary:hover {{ box-shadow: 0 15px 40px rgba(100, 116, 139, 0.4); }}
                .btn-group {{ display: flex; gap: 15px; flex-wrap: wrap; margin-top: 25px; }}
                .step {{ display: flex; gap: 20px; margin: 25px 0; padding: 20px; background: #f8fafc; border-radius: 10px; border-left: 4px solid #667eea; }}
                .step-number {{ width: 40px; height: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.2rem; flex-shrink: 0; }}
                .step-content {{ flex: 1; }}
                .step-content h4 {{ margin: 0 0 10px 0; color: #1e293b; }}
                .step-content p {{ margin: 0; color: #475569; }}
                .admin-section {{ background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 2px solid #f59e0b; }}
                .admin-section h2::before {{ content: '🔐'; }}
                .admin-section::before {{ background: linear-gradient(90deg, #f59e0b, #d97706); }}
                .accordion {{ border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; margin: 20px 0; }}
                .accordion-item {{ border-bottom: 1px solid #e5e7eb; }}
                .accordion-item:last-child {{ border-bottom: none; }}
                .accordion-header {{ background: #f8fafc; padding: 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.3s; }}
                .accordion-header:hover {{ background: #f1f5f9; }}
                .accordion-header h4 {{ margin: 0; color: #1e293b; }}
                .accordion-content {{ padding: 0 20px; max-height: 0; overflow: hidden; transition: max-height 0.3s ease, padding 0.3s ease; }}
                .accordion-content.open {{ padding: 20px; max-height: 1000px; }}
                .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }}
                .badge-get {{ background: #dbeafe; color: #1e40af; }}
                .badge-post {{ background: #d1fae5; color: #065f46; }}
                .badge-put {{ background: #fef3c7; color: #92400e; }}
                .badge-delete {{ background: #fee2e2; color: #991b1b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Semptify API Developer Portal</h1>
                    <p>Comprehensive documentation for integrating with the Semptify Housing Rights Platform. Build powerful applications to help tenants protect their rights through documentation, education, and evidence preservation.</p>
                    <div class="meta">
                        <span>📅 Version: {self.api_version}</span>
                        <span>🌐 Base URL: {self.base_url}</span>
                        <span>📧 Support: {self.contact_info['email']}</span>
                    </div>
                </div>
                
                <div class="nav">
                    <a href="#overview" class="nav-item active" data-section="overview">📖 Overview</a>
                    <a href="#authentication" class="nav-item" data-section="authentication">🔑 Authentication</a>
                    <a href="#modules" class="nav-item" data-section="modules">📚 API Modules</a>
                    <a href="#admin" class="nav-item" data-section="admin">🔐 Admin Guide</a>
                    <a href="#examples" class="nav-item" data-section="examples">💻 Code Examples</a>
                    <a href="/docs/swagger" class="nav-item" target="_blank">🔍 Swagger UI</a>
                    <a href="/docs/redoc" class="nav-item" target="_blank">📄 ReDoc</a>
                </div>
                
                <div id="overview" class="content-section active">
                    <div class="card">
                        <h2>Getting Started</h2>
                        <p>The Semptify API provides programmatic access to all platform features including document management, user authentication, case tracking, timeline events, and more. Our API is designed to be RESTful, intuitive, and well-documented.</p>
                        
                        <div class="step">
                            <div class="step-number">1</div>
                            <div class="step-content">
                                <h4>Get Your API Key</h4>
                                <p>Contact api@semptify.org to request API access. Include your use case and expected request volume.</p>
                            </div>
                        </div>
                        
                        <div class="step">
                            <div class="step-number">2</div>
                            <div class="step-content">
                                <h4>Authenticate Your Requests</h4>
                                <p>All API requests require authentication. We support JWT tokens and OAuth 2.0 for secure access.</p>
                            </div>
                        </div>
                        
                        <div class="step">
                            <div class="step-number">3</div>
                            <div class="step-content">
                                <h4>Make Your First Request</h4>
                                <p>Start with a simple endpoint like <code>GET /api/v1/health</code> to verify your connection.</p>
                            </div>
                        </div>
                        
                        <h3>Base URL</h3>
                        <p><code>{self.base_url}</code></p>
                        
                        <h3>Rate Limiting</h3>
                        <p>API requests are rate-limited based on your subscription tier:</p>
                        <ul>
                            <li><strong>Free tier:</strong> 100 requests/hour</li>
                            <li><strong>Basic tier:</strong> 1,000 requests/hour</li>
                            <li><strong>Premium tier:</strong> 10,000 requests/hour</li>
                        </ul>
                        
                        <div class="warning">
                            Exceeding rate limits will result in HTTP 429 responses. Implement exponential backoff in your client.
                        </div>
                        
                        <div class="btn-group">
                            <a href="/docs/openapi.json" class="btn">📥 Download OpenAPI Spec</a>
                            <a href="/docs/postman" class="btn btn-secondary">📥 Download Postman Collection</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Quick Start Guide</h2>
                        <p>Follow this quick start to make your first API call in under 5 minutes.</p>
                        
                        <div class="accordion">
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Step 1: Test Connection</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>curl -X GET {self.base_url}/api/v1/health</code></pre>
                                    <p>Expected response: <code>{{"status": "healthy", "version": "v1"}}</code></p>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Step 2: Authenticate</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>curl -X POST {self.base_url}/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{{"email": "your@email.com", "password": "your-password"}}'</code></pre>
                                    <p>Save the returned <code>token</code> for authenticated requests.</p>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Step 3: List Documents</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>curl -X GET {self.base_url}/api/v1/documents \\
  -H "Authorization: Bearer YOUR_TOKEN"</code></pre>
                                    <p>This returns a paginated list of documents for the authenticated user.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="authentication" class="content-section">
                    <div class="card">
                        <h2>Authentication Methods</h2>
                        <p>Semptify API supports multiple authentication methods for different use cases.</p>
                        
                        <h3>JWT Token Authentication</h3>
                        <p>Most API endpoints require a JWT token in the Authorization header:</p>
                        <pre><code>Authorization: Bearer YOUR_JWT_TOKEN</code></pre>
                        
                        <h3>OAuth 2.0</h3>
                        <p>For third-party integrations, use OAuth 2.0 with the following flow:</p>
                        <ul>
                            <li>Redirect users to <code>/oauth/authorize</code></li>
                            <li>User grants permission</li>
                            <li>Receive authorization code</li>
                            <li>Exchange code for access token at <code>/oauth/token</code></li>
                        </ul>
                        
                        <h3>Session Cookies</h3>
                        <p>For web applications, session-based authentication is available. The <code>semptify_session</code> cookie is set after login.</p>
                        
                        <div class="info">
                            JWT tokens expire after 24 hours. Refresh tokens are available for long-lived sessions.
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Security Best Practices</h2>
                        <ul>
                            <li>Never expose API keys or tokens in client-side code</li>
                            <li>Use HTTPS for all API requests</li>
                            <li>Implement proper token storage (httpOnly cookies for web, secure storage for mobile)</li>
                            <li>Validate all user input before sending to API</li>
                            <li>Use rate limiting to prevent abuse</li>
                            <li>Log all API requests for audit trails</li>
                        </ul>
                        
                        <div class="warning">
                            Never commit API keys or tokens to version control. Use environment variables or secret management systems.
                        </div>
                    </div>
                </div>
                
                <div id="modules" class="content-section">
                    <div class="card">
                        <h2>API Modules</h2>
                        <p>Browse all available API modules and their endpoints.</p>
                        <div class="module-list">
        """
        
        for module in modules_list:
            portal_html += f"""
                            <div class="module-item">
                                <div class="module-name">{module['name']}</div>
                                <div class="module-path">{module['base_path']}</div>
                                <div class="module-stats">
                                    <div class="stat">
                                        <span>📚</span>
                                        <span>{module['endpoint_count']} endpoints</span>
                                    </div>
                                    <div class="stat">
                                        <span>🏷️</span>
                                        <span>v{module['version']}</span>
                                    </div>
                                </div>
                                <div style="margin-top: 12px; color: #64748b; line-height: 1.6;">{module['description']}</div>
                            </div>
            """
        
        portal_html += f"""
                        </div>
                    </div>
                </div>
                
                <div id="admin" class="content-section">
                    <div class="card admin-section">
                        <h2>Admin Guide</h2>
                        <p>Comprehensive guide for administrators managing the Semptify API and platform.</p>
                        
                        <h3>Admin Dashboard Access</h3>
                        <p>Administrators can access the admin dashboard at <code>/admin</code>. Admin credentials are required:</p>
                        <ul>
                            <li><strong>Username:</strong> Set in <code>ADMIN_USERNAME</code> environment variable</li>
                            <li><strong>Password:</strong> Set in <code>ADMIN_PASSWORD</code> environment variable</li>
                            <li><strong>2FA:</strong> TOTP secret in <code>ADMIN_TOTP_SECRET</code></li>
                        </ul>
                        
                        <h3>User Management</h3>
                        <div class="accordion">
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>View All Users</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>GET /api/admin/users
Authorization: Bearer ADMIN_TOKEN</code></pre>
                                    <p>Returns paginated list of all users with their roles and status.</p>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Update User Role</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>PUT /api/admin/users/{{user_id}}/role
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json

{{
  "role": "advocate"
}}</code></pre>
                                    <p>Valid roles: <code>tenant</code>, <code>advocate</code>, <code>legal</code>, <code>admin</code>.</p>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Disable User Account</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>POST /api/admin/users/{{user_id}}/disable
Authorization: Bearer ADMIN_TOKEN</code></pre>
                                    <p>Disables a user account. User cannot login or access API.</p>
                                </div>
                            </div>
                        </div>
                        
                        <h3>System Monitoring</h3>
                        <p>Monitor system health and performance through dedicated endpoints:</p>
                        <ul>
                            <li><code>GET /api/health</code> - Overall system health</li>
                            <li><code>GET /api/health/database</code> - Database connection status</li>
                            <li><code>GET /api/health/storage</code> - Storage provider status</li>
                            <li><code>GET /api/metrics</code> - Performance metrics and usage stats</li>
                        </ul>
                        
                        <h3>Audit Logs</h3>
                        <p>All admin actions are logged to the <code>admin_audit_logs</code> table for compliance and security:</p>
                        <pre><code>GET /api/admin/audit-logs
Authorization: Bearer ADMIN_TOKEN
Query params: user_id, action, start_date, end_date</code></pre>
                        
                        <h3>Environment Variables</h3>
                        <p>Key environment variables for admin configuration:</p>
                        <ul>
                            <li><code>ADMIN_USERNAME</code> - Admin login username</li>
                            <li><code>ADMIN_PASSWORD</code> - Admin login password</li>
                            <li><code>ADMIN_TOTP_SECRET</code> - 2FA TOTP secret</li>
                            <li><code>ADMIN_PIN</code> - Elevated access PIN</li>
                            <li><code>SECRET_KEY</code> - JWT signing secret</li>
                            <li><code>SECURITY_MODE</code> - "open" or "enforced"</li>
                        </ul>
                        
                        <div class="warning">
                            Never use default admin credentials in production. Change all secrets immediately after deployment.
                        </div>
                        
                        <h3>Render Deployment</h3>
                        <p>For Render deployment, set environment variables in the Render dashboard:</p>
                        <ol>
                            <li>Go to Render dashboard → Semptify service</li>
                            <li>Click "Environment" tab</li>
                            <li>Add all required environment variables</li>
                            <li>Click "Save Changes"</li>
                            <li>Trigger manual deploy</li>
                        </ol>
                        
                        <h3>Database Management</h3>
                        <p>Access PostgreSQL database directly for advanced operations:</p>
                        <ul>
                            <li>Use Render dashboard → PostgreSQL → semptify_db</li>
                            <li>Or use psql with connection string from DATABASE_URL</li>
                            <li>Always use SSL mode: <code>sslmode=require</code></li>
                        </ul>
                        
                        <div class="success">
                            Regular database backups are automated by Render. Additional backups can be created manually.
                        </div>
                    </div>
                </div>
                
                <div id="examples" class="content-section">
                    <div class="card">
                        <h2>Code Examples</h2>
                        <p>Production-ready code examples in multiple languages.</p>
                        <div class="code-examples">
        """
        
        for example in code_examples_list:
            portal_html += f"""
                            <div class="code-example">
                                <h3>{example['description']}</h3>
                                <div class="code-block">
                                    <pre><code>{example['code']}</code></pre>
                                </div>
                            </div>
            """
        
        portal_html += f"""
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Additional Examples</h2>
                        <div class="accordion">
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Upload Document (Python)</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>import requests

# Upload a document
files = {{'file': open('lease.pdf', 'rb')}}
headers = {{'Authorization': f'Bearer {{token}}'}}

response = requests.post(
    '{self.base_url}/api/v1/documents/upload',
    files=files,
    headers=headers,
    data={{'document_type': 'lease'}}
)

if response.status_code == 200:
    print('Document uploaded successfully')
    print(f'Vault ID: {{response.json()["vault_id"]}}')</code></pre>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Create Case (JavaScript)</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>// Create a new case
const caseData = {{
  case_number: 'CASE-2024-001',
  property_address: '123 Main St',
  landlord_name: 'John Doe',
  issue_type: 'rent_increase',
  description: 'Illegal rent increase above legal limit'
}};

const response = await fetch('{self.base_url}/api/v1/cases', {{
  method: 'POST',
  headers: {{
    'Authorization': `Bearer ${{token}}`,
    'Content-Type': 'application/json'
  }},
  body: JSON.stringify(caseData)
}});

if (response.ok) {{
  const case = await response.json();
  console.log('Case created:', case.id);
}}</code></pre>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <div class="accordion-header" onclick="toggleAccordion(this)">
                                    <h4>Get Timeline Events (cURL)</h4>
                                    <span>▼</span>
                                </div>
                                <div class="accordion-content">
                                    <pre><code>curl -X GET '{self.base_url}/api/v1/timeline/unified' \\
  -H 'Authorization: Bearer YOUR_TOKEN' \\
  -H 'Content-Type: application/json'</code></pre>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                // Navigation handling
                document.querySelectorAll('.nav-item[data-section]').forEach(item => {{
                    item.addEventListener('click', (e) => {{
                        e.preventDefault();
                        
                        const section = item.getAttribute('data-section');
                        
                        // Hide all sections
                        document.querySelectorAll('.content-section').forEach(s => {{
                            s.classList.remove('active');
                        }});
                        
                        // Remove active from all nav items
                        document.querySelectorAll('.nav-item').forEach(nav => {{
                            nav.classList.remove('active');
                        }});
                        
                        // Show selected section
                        document.getElementById(section).classList.add('active');
                        
                        // Add active to clicked nav item
                        item.classList.add('active');
                    }});
                }});
                
                // Accordion toggle
                function toggleAccordion(header) {{
                    const content = header.nextElementSibling;
                    const isOpen = content.classList.contains('open');
                    
                    // Close all
                    document.querySelectorAll('.accordion-content').forEach(c => {{
                        c.classList.remove('open');
                    }});
                    
                    // Open clicked if it was closed
                    if (!isOpen) {{
                        content.classList.add('open');
                    }}
                }}
                
                // Smooth scroll for anchor links
                document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
                    anchor.addEventListener('click', function (e) {{
                        const targetId = this.getAttribute('href').substring(1);
                        const target = document.getElementById(targetId);
                        if (target) {{
                            e.preventDefault();
                            target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        """
        
        return portal_html
    
    def get_documentation_summary(self) -> Dict[str, Any]:
        """Get documentation summary statistics."""
        total_modules = len(self.modules)
        total_endpoints = sum(len(module.endpoints) for module in self.modules.values())
        total_examples = len(self.code_examples)
        
        return {
            "api_version": self.api_version,
            "base_url": self.base_url,
            "total_modules": total_modules,
            "total_endpoints": total_endpoints,
            "total_examples": total_examples,
            "modules": [
                {
                    "id": module.module_id,
                    "name": module.name,
                    "endpoint_count": len(module.endpoints)
                }
                for module in self.modules.values()
            ],
            "last_updated": utc_now().isoformat()
        }

# Global documentation generator instance
_documentation_generator: Optional[APIDocumentationGenerator] = None

def get_documentation_generator() -> APIDocumentationGenerator:
    """Get the global documentation generator instance."""
    global _documentation_generator
    
    if _documentation_generator is None:
        _documentation_generator = APIDocumentationGenerator()
        
        # Register default modules
        _register_default_modules()
    
    return _documentation_generator

def _register_default_modules():
    """Register default API modules."""
    generator = get_documentation_generator()
    
    # Authentication module
    auth_endpoints = [
        APIEndpoint(
            path="/auth/login",
            method="POST",
            summary="User Login",
            description="Authenticate user with email and password",
            parameters=[
                {
                    "name": "email",
                    "in": "body",
                    "required": True,
                    "schema": {"type": "string", "format": "email"}
                },
                {
                    "name": "password",
                    "in": "body",
                    "required": True,
                    "schema": {"type": "string", "minLength": 8}
                }
            ],
            request_body={
                "content": {
                    "application/json": {
                        "example": {
                            "email": "user@example.com",
                            "password": "securepassword123"
                        }
                    }
                }
            },
            responses={
                "200": {
                    "description": "Login successful",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "token": "jwt_token_here",
                                "user": {"id": "user_id", "email": "user@example.com"}
                            }
                        }
                    }
                },
                "401": {
                    "description": "Invalid credentials",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": False,
                                "error": "Invalid email or password"
                            }
                        }
                    }
                }
            },
            tags=["authentication"],
            security=[]
        )
    ]
    
    generator.register_module(APIModule(
        module_id="auth",
        name="Authentication",
        description="User authentication and authorization endpoints",
        endpoints=auth_endpoints,
        version="v1",
        base_path="/api/v1/auth"
    ))
    
    # Documents module
    docs_endpoints = [
        APIEndpoint(
            path="/documents",
            method="GET",
            summary="List Documents",
            description="Get list of user's documents with pagination",
            parameters=[
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "default": 1}
                },
                {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "default": 20, "maximum": 100}
                }
            ],
            responses={
                "200": {
                    "description": "Documents retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "documents": [],
                                "total": 0,
                                "page": 1,
                                "limit": 20
                            }
                        }
                    }
                }
            },
            tags=["documents"],
            security=["BearerAuth"]
        ),
        APIEndpoint(
            path="/documents/{document_id}",
            method="GET",
            summary="Get Document",
            description="Get specific document by ID",
            parameters=[
                {
                    "name": "document_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string", "format": "uuid"}
                }
            ],
            responses={
                "200": {
                    "description": "Document retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "id": "doc_id",
                                "filename": "lease_agreement.pdf",
                                "document_type": "lease",
                                "file_size": 1024000
                            }
                        }
                    }
                },
                "404": {
                    "description": "Document not found"
                }
            },
            tags=["documents"],
            security=["BearerAuth"]
        )
    ]
    
    generator.register_module(APIModule(
        module_id="documents",
        name="Documents",
        description="Document management endpoints",
        endpoints=docs_endpoints,
        version="v1",
        base_path="/api/v1/documents"
    ))
    
    # Add code examples
    generator.add_code_example(CodeExample(
        language="python",
        code="""
import requests

# Login to get token
login_response = requests.post('https://api.semptify.org/api/v1/auth/login', json={
    'email': 'your-email@example.com',
    'password': 'your-password'
})

if login_response.status_code == 200:
    token = login_response.json()['token']
    
    # Use token for authenticated requests
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get documents
    docs_response = requests.get(
        'https://api.semptify.org/api/v1/documents',
        headers=headers
    )
    
    if docs_response.status_code == 200:
        documents = docs_response.json()['documents']
        logger.info(f"Found {len(documents)} documents")
        """,
        description="Python - Basic API Usage",
        filename="basic_usage.py"
    ))
    
    generator.add_code_example(CodeExample(
        language="javascript",
        code="""
// Using fetch API
async function loginAndGetDocuments() {{
    try {{
        // Login
        const loginResponse = await fetch('https://api.semptify.org/api/v1/auth/login', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{
                email: 'your-email@example.com',
                password: 'your-password'
            }})
        }});
        
        if (!loginResponse.ok) {{
            throw new Error('Login failed');
        }}
        
        const loginData = await loginResponse.json();
        const token = loginData.token;
        
        // Get documents
        const docsResponse = await fetch('https://api.semptify.org/api/v1/documents', {{
            headers: {{
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }}
        }});
        
        if (docsResponse.ok) {{
            const documentsData = await docsResponse.json();
            console.log('Documents:', documentsData.documents);
        }}
    }} catch (error) {{
        console.error('Error:', error);
    }}
}}

// Call the function
loginAndGetDocuments();
        """,
        description="JavaScript - Fetch API Usage",
        filename="api_usage.js"
    ))

# Helper functions
def generate_openapi_spec() -> Dict[str, Any]:
    """Generate OpenAPI specification."""
    generator = get_documentation_generator()
    return generator.generate_openapi_spec()

def generate_postman_collection() -> Dict[str, Any]:
    """Generate Postman collection."""
    generator = get_documentation_generator()
    return generator.generate_postman_collection()

def generate_swagger_ui() -> str:
    """Generate Swagger UI HTML."""
    generator = get_documentation_generator()
    return generator.generate_swagger_ui()

def generate_redoc_html() -> str:
    """Generate ReDoc HTML."""
    generator = get_documentation_generator()
    return generator.generate_redoc_html()

def generate_developer_portal() -> str:
    """Generate developer portal HTML."""
    generator = get_documentation_generator()
    return generator.generate_developer_portal()

def get_documentation_summary() -> Dict[str, Any]:
    """Get documentation summary."""
    generator = get_documentation_generator()
    return generator.get_documentation_summary()
