"""
API Documentation Generator - Developer Portal
===========================================

Generates comprehensive API documentation and developer portal.
"""

import logging
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
        """Generate developer portal HTML."""
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
            <title>Semptify Developer Portal</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Inter', sans-serif; background: #f8fafc; color: #1a202c; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .header {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 30px; }}
                .header h1 {{ font-size: 2.5rem; font-weight: 700; color: #1e293b; margin-bottom: 10px; }}
                .header p {{ font-size: 1.1rem; color: #64748b; line-height: 1.6; }}
                .nav {{ display: flex; gap: 10px; margin-bottom: 30px; flex-wrap: wrap; }}
                .nav-item {{ background: white; padding: 12px 20px; border-radius: 8px; text-decoration: none; color: #1e293b; font-weight: 500; border: 2px solid transparent; transition: all 0.3s ease; }}
                .nav-item:hover {{ border-color: #1e293b; transform: translateY(-2px); }}
                .nav-item.active {{ background: #1e293b; color: white; }}
                .content-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
                .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .card h2 {{ font-size: 1.5rem; font-weight: 600; color: #1e293b; margin-bottom: 15px; }}
                .module-list {{ display: grid; gap: 15px; }}
                .module-item {{ background: #f1f5f9; padding: 20px; border-radius: 8px; border-left: 4px solid #3b82f6; }}
                .module-name {{ font-weight: 600; color: #1e293b; margin-bottom: 5px; }}
                .module-path {{ color: #64748b; font-family: monospace; background: #e5e7eb; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-bottom: 10px; }}
                .module-stats {{ display: flex; gap: 15px; font-size: 0.9rem; color: #64748b; }}
                .stat {{ display: flex; align-items: center; gap: 5px; }}
                .code-examples {{ margin-top: 30px; }}
                .code-example {{ background: #1e293b; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .code-example h3 {{ margin-bottom: 15px; }}
                .code-block {{ background: #f6f8fa; border: 1px solid #e5e7eb; border-radius: 6px; padding: 15px; overflow-x: auto; }}
                .code-block pre {{ margin: 0; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9rem; line-height: 1.5; }}
                .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 500; transition: all 0.3s ease; }}
                .btn:hover {{ background: #2563eb; transform: translateY(-1px); }}
                .btn-secondary {{ background: #64748b; }}
                .btn-secondary:hover {{ background: #475569; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Developer Portal</h1>
                    <p>Welcome to the Semptify API developer portal. Here you'll find comprehensive documentation, code examples, and tools to integrate with our housing rights platform.</p>
                </div>
                
                <div class="nav">
                    <a href="#overview" class="nav-item active">Overview</a>
                    <a href="#modules" class="nav-item">API Modules</a>
                    <a href="#examples" class="nav-item">Code Examples</a>
                    <a href="/docs/swagger" class="nav-item">Swagger UI</a>
                    <a href="/docs/redoc" class="nav-item">ReDoc</a>
                </div>
                
                <div id="overview" class="content-grid">
                    <div class="card">
                        <h2>Getting Started</h2>
                        <p>The Semptify API provides programmatic access to all platform features including document management, user authentication, search, and more.</p>
                        
                        <h3>Authentication</h3>
                        <p>All API requests require authentication using either JWT tokens or OAuth 2.0.</p>
                        
                        <h3>Base URL</h3>
                        <p><code>{self.base_url}</code></p>
                        
                        <h3>Rate Limiting</h3>
                        <p>API requests are rate-limited based on your subscription tier. Free tier: 100 requests/hour, Basic: 1000 requests/hour, Premium: 10000 requests/hour.</p>
                        
                        <div style="margin-top: 20px;">
                            <a href="/docs/openapi.json" class="btn">Download OpenAPI Spec</a>
                            <a href="/docs/postman" class="btn btn-secondary">Download Postman Collection</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Quick Links</h2>
                        <div style="display: grid; gap: 15px;">
                            <a href="/docs/swagger" class="btn" style="text-align: center;">Interactive Documentation</a>
                            <a href="/docs/redoc" class="btn btn-secondary" style="text-align: center;">ReDoc Documentation</a>
                        </div>
                    </div>
                </div>
                
                <div id="modules" class="card" style="display: none;">
                    <h2>API Modules</h2>
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
                            <div style="margin-top: 10px; color: #64748b;">{module['description']}</div>
                        </div>
            """
        
        portal_html += f"""
                    </div>
                </div>
                
                <div id="examples" class="card" style="display: none;">
                    <h2>Code Examples</h2>
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
            </div>
            
            <script>
                document.querySelectorAll('.nav-item').forEach(item => {{
                    item.addEventListener('click', (e) => {{
                        e.preventDefault();
                        
                        // Hide all content sections
                        document.querySelectorAll('.content-grid > div').forEach(section => {{
                            section.style.display = 'none';
                        }});
                        
                        // Remove active class from all nav items
                        document.querySelectorAll('.nav-item').forEach(nav => {{
                            nav.classList.remove('active');
                        }});
                        
                        // Show selected content
                        const targetId = item.getAttribute('href').substring(1);
                        const targetSection = document.getElementById(targetId);
                        if (targetSection) {{
                            targetSection.style.display = 'block';
                        }}
                        
                        // Add active class to clicked nav item
                        item.classList.add('active');
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
            "last_updated": datetime.now(timezone.utc).isoformat()
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
        print(f"Found {len(documents)} documents")
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
