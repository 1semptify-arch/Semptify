"""
Flask to FastAPI Module Converter
==================================

Converts Flask applications/blueprints to Semptify-compatible
FastAPI modules using the Positronic Mesh SDK.

Usage:
    python -m app.sdk.flask_converter path/to/flask_app.py --output my_module
    
Or programmatically:
    from app.sdk.flask_converter import FlaskConverter
    converter = FlaskConverter()
    result = converter.convert_file("old_flask_app.py", "new_module_name")
"""

import ast
import re
import os
import sys
import argparse
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FlaskRoute:
    """Represents a Flask route/endpoint"""
    path: str
    methods: List[str]
    function_name: str
    function_body: str
    decorators: List[str]
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    has_request_data: bool = False
    has_session: bool = False
    has_file_upload: bool = False
    returns_json: bool = False
    returns_template: bool = False
    

@dataclass
class FlaskBlueprint:
    """Represents a Flask blueprint"""
    name: str
    url_prefix: str
    routes: List[FlaskRoute] = field(default_factory=list)


@dataclass 
class FlaskAnalysis:
    """Results of analyzing a Flask file"""
    app_name: str
    blueprints: List[FlaskBlueprint]
    routes: List[FlaskRoute]  # Direct app routes
    imports: List[str]
    models: List[str]
    config_vars: Dict[str, Any]
    has_database: bool = False
    has_authentication: bool = False
    has_file_handling: bool = False
    original_code: str = ""


# =============================================================================
# FLASK CODE ANALYZER
# =============================================================================

class FlaskAnalyzer(ast.NodeVisitor):
    """Analyzes Flask code to extract routes, blueprints, etc."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.split('\n')
        self.routes: List[FlaskRoute] = []
        self.blueprints: List[FlaskBlueprint] = []
        self.imports: List[str] = []
        self.models: List[str] = []
        self.config_vars: Dict[str, Any] = {}
        self.app_name = "app"
        self.current_blueprint = None
        
    def analyze(self) -> FlaskAnalysis:
        """Run the analysis"""
        tree = ast.parse(self.source_code)
        self.visit(tree)
        
        return FlaskAnalysis(
            app_name=self.app_name,
            blueprints=self.blueprints,
            routes=self.routes,
            imports=self.imports,
            models=self.models,
            config_vars=self.config_vars,
            has_database="SQLAlchemy" in self.source_code or "db." in self.source_code,
            has_authentication="login" in self.source_code.lower() or "session" in self.source_code,
            has_file_handling="FileStorage" in self.source_code or "request.files" in self.source_code,
            original_code=self.source_code,
        )
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        # Detect Flask app creation
        if isinstance(node.value, ast.Call):
            if hasattr(node.value.func, 'id') and node.value.func.id == 'Flask':
                if node.targets and isinstance(node.targets[0], ast.Name):
                    self.app_name = node.targets[0].id
            
            # Detect Blueprint creation
            if hasattr(node.value.func, 'id') and node.value.func.id == 'Blueprint':
                if node.targets and isinstance(node.targets[0], ast.Name):
                    bp_name = node.targets[0].id
                    url_prefix = ""
                    for keyword in node.value.keywords:
                        if keyword.arg == 'url_prefix':
                            if isinstance(keyword.value, ast.Constant):
                                url_prefix = keyword.value.value
                    self.blueprints.append(FlaskBlueprint(
                        name=bp_name,
                        url_prefix=url_prefix,
                    ))
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check for route decorators
        for decorator in node.decorator_list:
            route_info = self._extract_route_info(decorator)
            if route_info:
                path, methods, is_blueprint = route_info
                
                # Get function body
                func_start = node.lineno - 1
                func_end = node.end_lineno if hasattr(node, 'end_lineno') else func_start + 20
                func_body = '\n'.join(self.source_lines[func_start:func_end])
                
                # Get docstring
                docstring = ast.get_docstring(node)
                
                # Analyze function body for patterns
                has_request_data = 'request.json' in func_body or 'request.form' in func_body
                has_session = 'session[' in func_body or 'session.' in func_body
                has_file_upload = 'request.files' in func_body
                returns_json = 'jsonify' in func_body or 'return {' in func_body
                returns_template = 'render_template' in func_body
                
                # Get parameters
                params = [arg.arg for arg in node.args.args if arg.arg != 'self']
                
                route = FlaskRoute(
                    path=path,
                    methods=methods,
                    function_name=node.name,
                    function_body=func_body,
                    decorators=[ast.dump(d) for d in node.decorator_list],
                    docstring=docstring,
                    parameters=params,
                    has_request_data=has_request_data,
                    has_session=has_session,
                    has_file_upload=has_file_upload,
                    returns_json=returns_json,
                    returns_template=returns_template,
                )
                
                if is_blueprint and self.blueprints:
                    self.blueprints[-1].routes.append(route)
                else:
                    self.routes.append(route)
        
        self.generic_visit(node)
    
    def _extract_route_info(self, decorator: ast.expr) -> Optional[Tuple[str, List[str], bool]]:
        """Extract route path and methods from decorator"""
        if isinstance(decorator, ast.Call):
            # Check if it's a route decorator
            func = decorator.func
            is_blueprint = False
            
            # @app.route(...) or @blueprint.route(...)
            if isinstance(func, ast.Attribute) and func.attr == 'route':
                if isinstance(func.value, ast.Name):
                    is_blueprint = func.value.id != self.app_name
                
                # Get path
                path = "/"
                if decorator.args:
                    if isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
                
                # Get methods
                methods = ["GET"]
                for keyword in decorator.keywords:
                    if keyword.arg == 'methods':
                        if isinstance(keyword.value, ast.List):
                            methods = [
                                elt.value if isinstance(elt, ast.Constant) else str(elt)
                                for elt in keyword.value.elts
                            ]
                
                return (path, methods, is_blueprint)
        
        return None


# =============================================================================
# FASTAPI MODULE GENERATOR
# =============================================================================

class FastAPIGenerator:
    """Generates FastAPI module code from Flask analysis"""
    
    def __init__(self, analysis: FlaskAnalysis, module_name: str, display_name: str):
        self.analysis = analysis
        self.module_name = module_name
        self.display_name = display_name
    
    def generate(self) -> str:
        """Generate complete FastAPI module"""
        sections = [
            self._generate_header(),
            self._generate_imports(),
            self._generate_module_definition(),
            self._generate_sdk_instance(),
            self._generate_pydantic_models(),
            self._generate_actions(),
            self._generate_event_handlers(),
            self._generate_init_function(),
            self._generate_router(),
            self._generate_exports(),
        ]
        
        return '\n\n'.join(filter(None, sections))
    
    def _generate_header(self) -> str:
        return f'''"""
{self.display_name} Module
{"=" * (len(self.display_name) + 7)}

Auto-converted from Flask to FastAPI Semptify Module
Original Flask app: {self.analysis.app_name}
Converted: {datetime.now().isoformat()}

This module integrates with the Semptify Positronic Mesh.
"""'''
    
    def _generate_imports(self) -> str:
        imports = [
            'import logging',
            'from datetime import datetime',
            'from typing import Any, Dict, List, Optional',
            '',
            'from fastapi import APIRouter, Cookie, HTTPException, UploadFile, File, Form',
            'from fastapi.responses import JSONResponse, HTMLResponse',
            'from pydantic import BaseModel',
            '',
            'from app.sdk import (',
            '    ModuleSDK,',
            '    ModuleDefinition,',
            '    ModuleCategory,',
            '    DocumentType,',
            '    PackType,',
            ')',
        ]
        
        # Add database imports if needed
        if self.analysis.has_database:
            imports.append('')
            imports.append('# Database imports (adjust as needed)')
            imports.append('# from app.core.database import get_db')
            imports.append('# from sqlalchemy.orm import Session')
        
        imports.append('')
        imports.append(f'logger = logging.getLogger(__name__)')
        
        return '\n'.join(imports)
    
    def _generate_module_definition(self) -> str:
        # Determine category
        category = "UTILITY"
        if self.analysis.has_database:
            category = "STORAGE"
        if self.analysis.has_authentication:
            category = "COMMUNICATION"
        if any("document" in r.path.lower() or "file" in r.path.lower() 
               for r in self.analysis.routes):
            category = "DOCUMENT"
        
        return f'''
# =============================================================================
# MODULE DEFINITION
# =============================================================================

module_definition = ModuleDefinition(
    name="{self.module_name}",
    display_name="{self.display_name}",
    description="Converted from Flask {self.analysis.app_name}",
    version="1.0.0",
    category=ModuleCategory.{category},
    
    # Document types this module can process
    handles_documents=[
        # Add document types if applicable
    ],
    
    # Info packs this module accepts
    accepts_packs=[
        PackType.USER_DATA,
    ],
    
    # Info packs this module produces
    produces_packs=[
        PackType.CUSTOM,
    ],
    
    depends_on=[],
    has_ui={str(any(r.returns_template for r in self.analysis.routes))},
    has_background_tasks=False,
    requires_auth={str(self.analysis.has_authentication)},
)'''
    
    def _generate_sdk_instance(self) -> str:
        return '''
# =============================================================================
# SDK INSTANCE
# =============================================================================

sdk = ModuleSDK(module_definition)'''
    
    def _generate_pydantic_models(self) -> str:
        """Generate Pydantic models from Flask routes"""
        models = []
        
        for route in self.analysis.routes:
            if route.has_request_data and "POST" in route.methods:
                model_name = self._to_pascal_case(route.function_name) + "Request"
                models.append(f'''
class {model_name}(BaseModel):
    """Request model for {route.function_name}"""
    data: Dict[str, Any] = {{}}
    # TODO: Add specific fields based on your Flask request.json/form structure''')
        
        if models:
            return '\n# =============================================================================\n# PYDANTIC MODELS\n# =============================================================================' + '\n'.join(models)
        return ''
    
    def _generate_actions(self) -> str:
        """Generate SDK actions from Flask routes"""
        actions = ['''
# =============================================================================
# SDK ACTIONS (Converted from Flask routes)
# =============================================================================''']
        
        for route in self.analysis.routes:
            action = self._convert_route_to_action(route)
            actions.append(action)
        
        # Add get_state action
        actions.append(f'''
@sdk.action(
    "get_state",
    description="Get current module state",
    produces=["{self.module_name}_state"],
)
async def get_state(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return module state for sync operations"""
    return {{
        "{self.module_name}_state": {{
            "active": True,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }}
    }}''')
        
        return '\n'.join(actions)
    
    def _convert_route_to_action(self, route: FlaskRoute) -> str:
        """Convert a Flask route to an SDK action"""
        action_name = route.function_name
        description = route.docstring or f"Converted from Flask {route.path}"
        
        # Clean up description
        description = description.replace('"', '\\"').split('\n')[0][:100]
        
        # Build action body
        body_lines = [
            f'    logger.info(f"{{module_definition.name}}: {action_name} for user {{user_id[:8]}}...")',
            '',
            '    # TODO: Migrate your Flask logic here',
            '    # Original Flask route: ' + route.path,
            '    # Methods: ' + ', '.join(route.methods),
        ]
        
        if route.has_request_data:
            body_lines.append('    # Note: Original used request.json or request.form')
            body_lines.append('    data = params.get("data", {})')
        
        if route.has_session:
            body_lines.append('    # Note: Original used Flask session - use user_id for user context')
        
        if route.has_file_upload:
            body_lines.append('    # Note: Original had file uploads - handle via separate endpoint')
        
        body_lines.append('')
        body_lines.append('    result = {')
        body_lines.append(f'        "action": "{action_name}",')
        body_lines.append('        "success": True,')
        body_lines.append('        "timestamp": datetime.utcnow().isoformat(),')
        body_lines.append('    }')
        body_lines.append('')
        body_lines.append('    return {"result": result}')
        
        body = '\n'.join(body_lines)
        
        return f'''
@sdk.action(
    "{action_name}",
    description="{description}",
    produces=["result"],
)
async def {action_name}(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Converted from Flask route: {route.path}
    Methods: {', '.join(route.methods)}
    """
{body}'''
    
    def _generate_event_handlers(self) -> str:
        return '''
# =============================================================================
# EVENT HANDLERS
# =============================================================================

@sdk.on_event("workflow_started")
async def on_workflow_started(event_type: str, data: Dict[str, Any]):
    """React when workflows start"""
    logger.debug(f"{module_definition.name}: Workflow started - {data.get(\'workflow_id\')}")'''
    
    def _generate_init_function(self) -> str:
        return '''
# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():
    """Initialize this module - call from main.py on startup"""
    sdk.initialize()
    logger.info(f"✅ {module_definition.display_name} module ready")'''
    
    def _generate_router(self) -> str:
        """Generate FastAPI router from Flask routes"""
        router_code = ['''
# =============================================================================
# FASTAPI ROUTER (REST API Endpoints)
# =============================================================================

router = APIRouter()''']
        
        for route in self.analysis.routes:
            endpoint = self._convert_route_to_endpoint(route)
            router_code.append(endpoint)
        
        return '\n'.join(router_code)
    
    def _convert_route_to_endpoint(self, route: FlaskRoute) -> str:
        """Convert Flask route to FastAPI endpoint"""
        # Convert Flask path params to FastAPI style
        path = route.path
        path = re.sub(r'<(\w+):(\w+)>', r'{\2}', path)  # <type:name> -> {name}
        path = re.sub(r'<(\w+)>', r'{\1}', path)  # <name> -> {name}
        
        method = route.methods[0].lower()
        func_name = f"api_{route.function_name}"
        
        # Build parameters
        params = ['semptify_uid: Optional[str] = Cookie(default=None)']
        
        # Add path parameters
        path_params = re.findall(r'\{(\w+)\}', path)
        for param in path_params:
            params.insert(0, f'{param}: str')
        
        # Add body for POST/PUT
        if method in ['post', 'put', 'patch']:
            if route.has_request_data:
                model_name = self._to_pascal_case(route.function_name) + "Request"
                params.insert(0, f'request: {model_name}')
        
        params_str = ',\n    '.join(params)
        
        # Build body
        body_lines = [
            '    user_id = semptify_uid or "anonymous"',
        ]
        
        if method in ['post', 'put', 'patch'] and route.has_request_data:
            body_lines.append('    result = await {}(user_id, {{"data": request.dict()}}, {{}})'.format(
                route.function_name
            ))
        else:
            body_lines.append('    result = await {}(user_id, {{}}, {{}})'.format(route.function_name))
        
        body_lines.append('    return result')
        body = '\n'.join(body_lines)
        
        docstring = route.docstring or f"API endpoint converted from Flask {route.path}"
        docstring = docstring.split('\n')[0][:80]
        
        return f'''

@router.{method}("{path}")
async def {func_name}(
    {params_str},
):
    """{docstring}"""
{body}'''
    
    def _generate_exports(self) -> str:
        return f'''
# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "sdk",
    "module_definition",
    "initialize",
    "router",
]'''
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase"""
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)


# =============================================================================
# MAIN CONVERTER CLASS
# =============================================================================

class FlaskConverter:
    """
    Main converter class that orchestrates Flask to FastAPI conversion.
    
    Usage:
        converter = FlaskConverter()
        result = converter.convert_file("flask_app.py", "my_module")
        # or
        result = converter.convert_code(flask_code_string, "my_module")
    """
    
    def convert_file(
        self,
        flask_file: str,
        module_name: str,
        display_name: str = None,
        output_dir: str = None,
    ) -> str:
        """Convert a Flask file to a FastAPI module"""
        with open(flask_file, 'r', encoding='utf-8') as f:
            flask_code = f.read()
        
        display_name = display_name or self._generate_display_name(module_name)
        
        result = self.convert_code(flask_code, module_name, display_name)
        
        if output_dir:
            self._write_output(result, module_name, output_dir)
        
        return result
    
    def convert_code(
        self,
        flask_code: str,
        module_name: str,
        display_name: str = None,
    ) -> str:
        """Convert Flask code string to FastAPI module"""
        display_name = display_name or self._generate_display_name(module_name)
        
        # Analyze Flask code
        analyzer = FlaskAnalyzer(flask_code)
        analysis = analyzer.analyze()
        
        logger.info(f"📊 Analyzed Flask app: {analysis.app_name}")
        logger.info(f"   Routes: {len(analysis.routes)}")
        logger.info(f"   Blueprints: {len(analysis.blueprints)}")
        
        # Generate FastAPI module
        generator = FastAPIGenerator(analysis, module_name, display_name)
        fastapi_code = generator.generate()
        
        return fastapi_code
    
    def _generate_display_name(self, module_name: str) -> str:
        """Generate display name from module name"""
        return ' '.join(word.title() for word in module_name.split('_'))
    
    def _write_output(self, code: str, module_name: str, output_dir: str):
        """Write generated code to file"""
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"{module_name}.py")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        logger.info(f"✅ Generated module: {filepath}")
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ✅ Flask to FastAPI Conversion Complete!                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Output: {filepath:<50} ║
║                                                              ║
║  Next Steps:                                                 ║
║  1. Review and customize the generated module                ║
║  2. Add to main.py startup:                                  ║
║                                                              ║
║     from app.modules.{module_name} import initialize         ║
║     initialize()                                             ║
║                                                              ║
║  3. Add router to main.py:                                   ║
║                                                              ║
║     from app.modules.{module_name} import router             ║
║     app.include_router(router, prefix="/api/{module_name}")  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Convert Flask app/blueprint to Semptify FastAPI module"
    )
    
    parser.add_argument(
        "flask_file",
        help="Path to Flask Python file to convert"
    )
    parser.add_argument(
        "--module-name", "-m",
        help="Name for the new module (snake_case)",
        default=None,
    )
    parser.add_argument(
        "--display-name", "-d",
        help="Display name for the module",
        default=None,
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: app/modules)",
        default="app/modules",
    )
    parser.add_argument(
        "--print-only", "-p",
        action="store_true",
        help="Print output instead of writing to file",
    )
    parser.add_argument(
        "--analyze-only", "-a",
        action="store_true",
        help="Only analyze the Flask file, don't generate",
    )
    
    args = parser.parse_args()
    
    # Determine module name
    if args.module_name:
        module_name = args.module_name
    else:
        # Generate from filename
        basename = os.path.basename(args.flask_file)
        module_name = os.path.splitext(basename)[0]
        module_name = re.sub(r'[^a-z0-9_]', '_', module_name.lower())
    
    converter = FlaskConverter()
    
    if args.analyze_only:
        # Just analyze
        with open(args.flask_file, 'r', encoding='utf-8') as f:
            flask_code = f.read()
        
        analyzer = FlaskAnalyzer(flask_code)
        analysis = analyzer.analyze()
        
        print(f"""
Flask Analysis Report
=====================
App Name: {analysis.app_name}
Routes: {len(analysis.routes)}
Blueprints: {len(analysis.blueprints)}
Has Database: {analysis.has_database}
Has Authentication: {analysis.has_authentication}
Has File Handling: {analysis.has_file_handling}

Routes Found:
""")
        for route in analysis.routes:
            print(f"  {', '.join(route.methods):<10} {route.path:<30} -> {route.function_name}")
        
        for bp in analysis.blueprints:
            print(f"\nBlueprint: {bp.name} (prefix: {bp.url_prefix})")
            for route in bp.routes:
                print(f"  {', '.join(route.methods):<10} {route.path:<30} -> {route.function_name}")
    
    elif args.print_only:
        result = converter.convert_file(
            args.flask_file,
            module_name,
            args.display_name,
        )
        print(result)
    
    else:
        converter.convert_file(
            args.flask_file,
            module_name,
            args.display_name,
            args.output_dir,
        )


if __name__ == "__main__":
    main()
