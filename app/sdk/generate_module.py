#!/usr/bin/env python
"""
Semptify Module Generator CLI
=============================

Generates new module scaffolding for the Positronic Mesh.

Usage:
    python -m app.sdk.generate_module my_module "My Module" "Description of my module"
    
Or with options:
    python -m app.sdk.generate_module my_module "My Module" "Description" --category legal --has-ui
"""

import argparse
import os
import sys
from datetime import datetime


TEMPLATE = '''"""
{display_name} Module
{"=" * (len("{display_name}") + 7)}

{description}

Generated: {timestamp}

This module integrates with the Semptify Positronic Mesh.
See docs/MODULE_DEVELOPMENT.md for documentation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
    DocumentType,
    PackType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MODULE DEFINITION
# =============================================================================

module_definition = ModuleDefinition(
    name="{module_name}",
    display_name="{display_name}",
    description="{description}",
    version="1.0.0",
    category=ModuleCategory.{category},
    
    # Document types this module can process
    handles_documents=[
        {handles_documents}
    ],
    
    # Info packs this module accepts from other modules
    accepts_packs=[
        {accepts_packs}
    ],
    
    # Info packs this module produces for other modules
    produces_packs=[
        {produces_packs}
    ],
    
    # Other modules this depends on
    depends_on=[
        {depends_on}
    ],
    
    has_ui={has_ui},
    has_background_tasks={has_background_tasks},
    requires_auth=True,
)


# =============================================================================
# SDK INSTANCE
# =============================================================================

sdk = ModuleSDK(module_definition)


# =============================================================================
# ACTIONS
# =============================================================================

@sdk.action(
    "process",
    description="Main processing action for {display_name}",
    required_params=["data"],
    produces=["result"],
)
async def process(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main processing action.
    
    Args:
        user_id: The user making the request
        params: Parameters including 'data'
        context: Workflow context
    
    Returns:
        Dict with 'result' key
    """
    logger.info(f"{{module_definition.name}}: Processing for user {{user_id[:8]}}...")
    
    data = params.get("data", {{}})
    
    # TODO: Implement your processing logic here
    result = {{
        "processed": True,
        "input_data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }}
    
    return {{"result": result}}


@sdk.action(
    "get_state",
    description="Get current module state",
    produces=["{module_name}_state"],
)
async def get_state(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return module state for sync operations"""
    return {{
        "{module_name}_state": {{
            "active": True,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }}
    }}


# TODO: Add more actions as needed
# @sdk.action("another_action", ...)
# async def another_action(user_id, params, context):
#     pass


# =============================================================================
# EVENT HANDLERS (Optional)
# =============================================================================

@sdk.on_event("workflow_started")
async def on_workflow_started(event_type: str, data: Dict[str, Any]):
    """React when workflows start"""
    logger.debug(f"{{module_definition.name}}: Workflow started - {{data.get('workflow_id')}}")


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():
    """Initialize this module - call from main.py on startup"""
    sdk.initialize()
    logger.info(f"✅ {{module_definition.display_name}} module ready")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "sdk",
    "module_definition",
    "initialize",
    "process",
    "get_state",
]


# =============================================================================
# OPTIONAL: FastAPI Router
# =============================================================================
{router_section}
'''

ROUTER_TEMPLATE = '''
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ProcessRequest(BaseModel):
    data: Dict[str, Any] = {}


@router.post("/process")
async def api_process(
    request: ProcessRequest,
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """API endpoint to process data"""
    user_id = semptify_uid or "anonymous"
    result = await process(user_id, {"data": request.data}, {})
    return result


@router.get("/status")
async def api_status(
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """Get module status"""
    user_id = semptify_uid or "anonymous"
    return await get_state(user_id, {}, {})
'''


def generate_module(
    module_name: str,
    display_name: str,
    description: str,
    category: str = "UTILITY",
    has_ui: bool = False,
    has_background_tasks: bool = False,
    handles_documents: list = None,
    accepts_packs: list = None,
    produces_packs: list = None,
    depends_on: list = None,
    include_router: bool = False,
    output_dir: str = None,
) -> str:
    """Generate a new module file"""
    
    # Format lists
    def format_list(items, prefix=""):
        if not items:
            return "# Add items here"
        return "\n        ".join(f'{prefix}.{item},' for item in items)
    
    # Build template
    content = TEMPLATE.format(
        module_name=module_name,
        display_name=display_name,
        description=description,
        timestamp=datetime.now().isoformat(),
        category=category.upper(),
        has_ui=str(has_ui),
        has_background_tasks=str(has_background_tasks),
        handles_documents=format_list(handles_documents, "DocumentType") if handles_documents else "# DocumentType.LEASE,",
        accepts_packs=format_list(accepts_packs, "PackType") if accepts_packs else "# PackType.USER_DATA,",
        produces_packs=format_list(produces_packs, "PackType") if produces_packs else "# PackType.ANALYSIS_RESULT,",
        depends_on=', '.join(f'"{d}"' for d in (depends_on or [])) or '# "documents",',
        router_section=ROUTER_TEMPLATE if include_router else "# Uncomment to add API endpoints\n# from fastapi import APIRouter\n# router = APIRouter()",
    )
    
    # Write file if output_dir provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"{module_name}.py")
        with open(filepath, "w") as f:
            f.write(content)
        print(f"✅ Generated module: {filepath}")
        
        # Print next steps
        print(f"""
📋 Next Steps:
1. Edit {filepath} to implement your logic
2. Add to main.py startup:
   
   from app.modules.{module_name} import initialize as init_{module_name}
   init_{module_name}()
   
3. If using router, add to main.py:
   
   from app.modules.{module_name} import router as {module_name}_router
   app.include_router({module_name}_router, prefix="/api/{module_name.replace('_', '-')}", tags=["{display_name}"])
""")
    
    return content


def main():
    parser = argparse.ArgumentParser(
        description="Generate a new Semptify module"
    )
    
    parser.add_argument(
        "module_name",
        help="Module name in snake_case (e.g., payment_tracking)"
    )
    parser.add_argument(
        "display_name",
        help="Human-readable display name (e.g., 'Payment Tracking')"
    )
    parser.add_argument(
        "description",
        help="Description of what the module does"
    )
    parser.add_argument(
        "--category",
        choices=["document", "legal", "calendar", "communication", 
                 "analysis", "storage", "ui", "utility", "ai", "integration"],
        default="utility",
        help="Module category (default: utility)"
    )
    parser.add_argument(
        "--has-ui",
        action="store_true",
        help="Module has a UI component"
    )
    parser.add_argument(
        "--has-background-tasks",
        action="store_true",
        help="Module runs background tasks"
    )
    parser.add_argument(
        "--with-router",
        action="store_true",
        help="Include FastAPI router boilerplate"
    )
    parser.add_argument(
        "--output-dir",
        default="app/modules",
        help="Output directory (default: app/modules)"
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print template without writing file"
    )
    
    args = parser.parse_args()
    
    output_dir = None if args.print_only else args.output_dir
    
    content = generate_module(
        module_name=args.module_name,
        display_name=args.display_name,
        description=args.description,
        category=args.category,
        has_ui=args.has_ui,
        has_background_tasks=args.has_background_tasks,
        include_router=args.with_router,
        output_dir=output_dir,
    )
    
    if args.print_only:
        print(content)


if __name__ == "__main__":
    main()
