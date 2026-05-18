"""
Page Index API Router
Provides dynamic scanning and listing of all HTML pages across the workspace.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/pages", tags=["Page Index"])


class PageInfo(BaseModel):
    """Information about an HTML page"""
    name: str
    path: str
    full_path: str
    repo: str
    type: str
    size: int
    date: str
    
    
class PageIndexResponse(BaseModel):
    """Response containing list of pages"""
    pages: List[PageInfo]
    total: int
    repos: List[str]
    types: List[str]


def classify_page_type(path: str) -> str:
    """Classify page type based on path"""
    path_lower = path.lower()
    
    if '_archive' in path_lower or 'backup' in path_lower:
        return 'archive'
    elif 'admin' in path_lower or 'mission_control' in path_lower:
        return 'admin'
    elif 'legal' in path_lower or 'court' in path_lower or 'motion' in path_lower or 'eviction' in path_lower:
        return 'legal'
    elif 'tenant' in path_lower:
        return 'tenant'
    elif 'dakota' in path_lower:
        return 'dakota'
    elif 'template' in path_lower or 'component' in path_lower:
        return 'template'
    else:
        return 'static'


def get_repo_from_path(full_path: str, base_path: str = "C:\\Semptify") -> str:
    """Extract repository name from full path"""
    try:
        rel_path = Path(full_path).relative_to(base_path)
        parts = rel_path.parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    return "Unknown"


@router.get("/scan", response_model=PageIndexResponse)
async def scan_html_pages(
    base_path: str = Query(default="C:\\Semptify", description="Base path to scan"),
    include_templates: bool = Query(default=True, description="Include template files"),
    include_archive: bool = Query(default=True, description="Include archive/backup files"),
):
    """
    Scan all directories for HTML files and return a complete index.
    """
    pages = []
    repos_set = set()
    types_set = set()
    
    base = Path(base_path)
    
    if not base.exists():
        return PageIndexResponse(pages=[], total=0, repos=[], types=[])
    
    for html_file in base.rglob("*.html"):
        try:
            # Skip node_modules, .git, __pycache__, etc.
            path_str = str(html_file)
            if any(skip in path_str for skip in ['node_modules', '.git', '__pycache__', 'htmlcov', 'venv', '.venv']):
                continue
            
            # Get relative path from base
            rel_path = html_file.relative_to(base)
            repo = get_repo_from_path(str(html_file), base_path)
            page_type = classify_page_type(str(rel_path))
            
            # Filter based on options
            if not include_templates and page_type == 'template':
                continue
            if not include_archive and page_type == 'archive':
                continue
            
            # Get file stats
            stat = html_file.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
            
            page = PageInfo(
                name=html_file.name,
                path=str(rel_path).replace('\\', '/'),
                full_path=str(html_file),
                repo=repo,
                type=page_type,
                size=stat.st_size,
                date=modified
            )
            
            pages.append(page)
            repos_set.add(repo)
            types_set.add(page_type)
            
        except Exception as e:
            # Skip files we can't read
            continue
    
    # Sort by path
    pages.sort(key=lambda p: p.path)
    
    return PageIndexResponse(
        pages=pages,
        total=len(pages),
        repos=sorted(list(repos_set)),
        types=sorted(list(types_set))
    )


@router.get("/fastapi", response_model=PageIndexResponse)
async def scan_fastapi_pages():
    """
    Scan only the Semptify-FastAPI static folder for HTML pages.
    """
    pages = []
    repos_set = set()
    types_set = set()
    
    # Scan both static and templates folders
    scan_paths = [
        Path("static"),
        Path("app/templates"),
        Path("semptify_dakota_eviction/app/templates")
    ]
    
    for scan_path in scan_paths:
        if not scan_path.exists():
            continue
            
        for html_file in scan_path.rglob("*.html"):
            try:
                page_type = classify_page_type(str(html_file))
                stat = html_file.stat()
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
                
                page = PageInfo(
                    name=html_file.name,
                    path=str(html_file).replace('\\', '/'),
                    full_path=str(html_file.absolute()),
                    repo="Semptify-FastAPI",
                    type=page_type,
                    size=stat.st_size,
                    date=modified
                )
                
                pages.append(page)
                repos_set.add("Semptify-FastAPI")
                types_set.add(page_type)
                
            except Exception:
                continue
    
    pages.sort(key=lambda p: p.path)
    
    return PageIndexResponse(
        pages=pages,
        total=len(pages),
        repos=sorted(list(repos_set)),
        types=sorted(list(types_set))
    )


@router.get("/stats")
async def get_page_stats(base_path: str = Query(default="C:\\Semptify")):
    """
    Get statistics about HTML pages without full page data.
    """
    base = Path(base_path)
    
    if not base.exists():
        return {"error": "Path not found"}
    
    total_files = 0
    total_size = 0
    repos = {}
    types = {}
    
    for html_file in base.rglob("*.html"):
        path_str = str(html_file)
        if any(skip in path_str for skip in ['node_modules', '.git', '__pycache__', 'htmlcov']):
            continue
            
        try:
            stat = html_file.stat()
            total_files += 1
            total_size += stat.st_size
            
            repo = get_repo_from_path(str(html_file), base_path)
            page_type = classify_page_type(str(html_file))
            
            repos[repo] = repos.get(repo, 0) + 1
            types[page_type] = types.get(page_type, 0) + 1
            
        except Exception:
            continue
    
    return {
        "total_files": total_files,
        "total_size": total_size,
        "total_size_formatted": format_size(total_size),
        "by_repository": repos,
        "by_type": types
    }


def format_size(size: int) -> str:
    """Format size in human readable format"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


@router.get("/search")
async def search_pages(
    q: str = Query(..., description="Search query"),
    repo: Optional[str] = Query(default=None, description="Filter by repository"),
    page_type: Optional[str] = Query(default=None, description="Filter by type"),
    base_path: str = Query(default="C:\\Semptify"),
):
    """
    Search for HTML pages by name or path.
    """
    base = Path(base_path)
    results = []
    query_lower = q.lower()
    
    for html_file in base.rglob("*.html"):
        path_str = str(html_file)
        if any(skip in path_str for skip in ['node_modules', '.git', '__pycache__', 'htmlcov']):
            continue
        
        # Check if matches search query
        if query_lower not in html_file.name.lower() and query_lower not in path_str.lower():
            continue
        
        try:
            file_repo = get_repo_from_path(str(html_file), base_path)
            file_type = classify_page_type(str(html_file))
            
            # Apply filters
            if repo and file_repo != repo:
                continue
            if page_type and file_type != page_type:
                continue
            
            rel_path = html_file.relative_to(base)
            stat = html_file.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
            
            results.append(PageInfo(
                name=html_file.name,
                path=str(rel_path).replace('\\', '/'),
                full_path=str(html_file),
                repo=file_repo,
                type=file_type,
                size=stat.st_size,
                date=modified
            ))
            
        except Exception:
            continue
    
    return {
        "query": q,
        "results": results,
        "count": len(results)
    }
