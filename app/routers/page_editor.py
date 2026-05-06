"""
Page Editor API Router
Interactive editor for static HTML and Jinja2 templates
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect

router = APIRouter(prefix="/api/editor", tags=["page-editor"])

# Base paths for editable files
STATIC_PATH = Path("static")
TEMPLATES_PATH = Path("app/templates")


class FileInfo(BaseModel):
    name: str
    path: str
    folder: str
    type: str
    size: int
    modified: float


class FileContent(BaseModel):
    path: str
    content: str
    type: str


class SaveRequest(BaseModel):
    path: str
    content: str


class FileListResponse(BaseModel):
    static: List[FileInfo]
    templates: List[FileInfo]


def get_file_type(filename: str) -> str:
    """Determine file type from extension"""
    if filename.endswith('.html'):
        return 'html'
    elif filename.endswith('.jinja'):
        return 'jinja'
    elif filename.endswith('.css'):
        return 'css'
    elif filename.endswith('.js'):
        return 'javascript'
    elif filename.endswith('.py'):
        return 'python'
    elif filename.endswith('.md'):
        return 'markdown'
    else:
        return 'text'


def scan_directory(base_path: Path, rel_prefix: str = "") -> List[FileInfo]:
    """Recursively scan directory for editable files"""
    files = []
    editable_extensions = {'.html', '.css', '.js', '.py', '.md', '.jinja', '.json'}
    
    if not base_path.exists():
        return files
    
    for item in base_path.rglob('*'):
        if item.is_file() and item.suffix in editable_extensions:
            # Calculate relative path from project root
            rel_path = str(item.relative_to(Path.cwd()))
            
            # Determine folder for grouping
            try:
                folder = str(item.parent.relative_to(base_path))
                if folder == '.':
                    folder = 'Root'
            except ValueError:
                folder = 'Other'
            
            stat = item.stat()
            files.append(FileInfo(
                name=item.name,
                path=rel_path,
                folder=folder,
                type=get_file_type(item.name),
                size=stat.st_size,
                modified=stat.st_mtime
            ))
    
    # Sort by folder then name
    files.sort(key=lambda f: (f.folder, f.name))
    return files


@router.get("/files", response_model=FileListResponse)
async def list_files():
    """List all editable files in static and templates directories"""
    try:
        static_files = scan_directory(STATIC_PATH)
        template_files = scan_directory(TEMPLATES_PATH)
        
        return FileListResponse(
            static=static_files,
            templates=template_files
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning files: {str(e)}")


@router.get("/file")
async def get_file(path: str = Query(..., description="File path relative to project root")):
    """Get content of a specific file"""
    try:
        # Security: Ensure path is within project directory
        file_path = Path(path).resolve()
        project_root = Path.cwd().resolve()
        
        # Check if path is within project
        try:
            file_path.relative_to(project_root)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: Path outside project")
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is not text-readable")
        
        return FileContent(
            path=path,
            content=content,
            type=get_file_type(file_path.name)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.post("/save")
async def save_file(request: SaveRequest):
    """Save content to a file"""
    try:
        # Security: Ensure path is within project directory
        file_path = Path(request.path).resolve()
        project_root = Path.cwd().resolve()
        
        # Check if path is within project
        try:
            file_path.relative_to(project_root)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: Path outside project")
        
        # Check if parent directory exists
        if not file_path.parent.exists():
            raise HTTPException(status_code=400, detail=f"Directory does not exist: {file_path.parent}")
        
        # Write file content
        file_path.write_text(request.content, encoding='utf-8')
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Saved {request.path}",
                "path": request.path,
                "size": len(request.content)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")


@router.post("/preview")
async def preview_file(request: SaveRequest):
    """Generate preview of HTML content"""
    try:
        content = request.content
        
        # For Jinja2 templates, add base template wrapper for preview
        if request.path.endswith('.jinja') or request.path.endswith('_ssot.html'):
            # Simple preview - just return the raw template
            # In production, you'd render with sample data
            preview_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Template Preview</title>
                <style>
                    body {{ font-family: sans-serif; padding: 2rem; background: #f5f5f5; }}
                    .preview-notice {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 1rem; margin-bottom: 1rem; border-radius: 4px; }}
                    .template-content {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                </style>
            </head>
            <body>
                <div class="preview-notice">
                    <strong>⚠️ Template Preview</strong><br>
                    Jinja2 templates require server-side rendering. This preview shows the raw template syntax.
                </div>
                <div class="template-content">
                    <pre>{content}</pre>
                </div>
            </body>
            </html>
            """
            return JSONResponse(content={"html": preview_html})
        
        # For static HTML, return as-is (with safety checks)
        if request.path.endswith('.html'):
            return JSONResponse(content={"html": content})
        
        # For other files, wrap in preview
        preview_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>File Preview</title>
            <style>
                body {{ font-family: monospace; padding: 2rem; background: #1e1e1e; color: #d4d4d4; }}
                pre {{ white-space: pre-wrap; word-wrap: break-word; }}
            </style>
        </head>
        <body>
            <pre>{content}</pre>
        </body>
        </html>
        """
        return JSONResponse(content={"html": preview_html})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")


@router.get("/search")
async def search_files(
    q: str = Query(..., min_length=2, description="Search query"),
    type: Optional[str] = Query(None, description="File type filter")
):
    """Search files by name or content"""
    try:
        all_files = scan_directory(STATIC_PATH) + scan_directory(TEMPLATES_PATH)
        results = []
        
        query = q.lower()
        
        for file in all_files:
            # Search in filename
            if query in file.name.lower():
                results.append(file)
                continue
            
            # Search in content (limit to first 100 matches for performance)
            if len(results) < 100:
                try:
                    file_path = Path(file.path)
                    if file_path.exists() and file_path.stat().st_size < 1024 * 1024:  # Skip files > 1MB
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if query in content.lower():
                            results.append(file)
                except:
                    pass
        
        return {"results": results[:100], "total": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")


@router.get("/page")
def editor_page():
    """Redirect to the page editor UI"""
    return ssot_redirect("/admin/page-editor.html", context="page_editor redirect")
