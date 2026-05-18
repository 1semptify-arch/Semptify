"""
Auto Mode Router
Manages auto mode configuration and status for users.
Provides endpoints to toggle auto mode and check configuration.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.core.database import get_db_session
from app.services.auto_mode_orchestrator import AutoModeOrchestrator

router = APIRouter(prefix="/api/auto-mode", tags=["auto-mode"])

# In-memory storage for user auto mode preferences
_user_preferences: Dict[str, Dict[str, Any]] = {}


class AutoModeConfig(BaseModel):
    """Auto mode configuration"""
    enabled: bool = True
    auto_generate_timeline: bool = True
    auto_generate_calendar: bool = True
    auto_identify_complaints: bool = True
    auto_assess_rights: bool = True
    auto_detect_missteps: bool = True
    auto_suggest_tactics: bool = True


class AutoModeStatus(BaseModel):
    """Status of auto mode"""
    enabled: bool
    config: AutoModeConfig
    last_analysis: Optional[str] = None
    analysis_count: int = 0


def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """Get or create user auto mode preferences"""
    if user_id not in _user_preferences:
        _user_preferences[user_id] = {
            "enabled": True,
            "config": AutoModeConfig().dict(),
            "analysis_count": 0,
            "last_analysis": None
        }
    return _user_preferences[user_id]


@router.get("/status")
async def get_auto_mode_status(user: StorageUser = Depends(require_user)):
    """Get current auto mode status for user"""
    prefs = get_user_preferences(user.sub)
    return AutoModeStatus(
        enabled=prefs["enabled"],
        config=AutoModeConfig(**prefs["config"]),
        last_analysis=prefs.get("last_analysis"),
        analysis_count=prefs.get("analysis_count", 0)
    )


@router.post("/toggle")
async def toggle_auto_mode(enabled: bool, user: StorageUser = Depends(require_user)):
    """Toggle auto mode on/off for user"""
    prefs = get_user_preferences(user.sub)
    prefs["enabled"] = enabled
    
    return {
        "status": "success",
        "auto_mode_enabled": enabled,
        "message": f"Auto mode {'enabled' if enabled else 'disabled'}"
    }


@router.post("/config")
async def update_auto_mode_config(
    config: AutoModeConfig,
    user: StorageUser = Depends(require_user)
):
    """Update auto mode configuration"""
    prefs = get_user_preferences(user.sub)
    prefs["config"] = config.dict()
    
    return {
        "status": "success",
        "config": config,
        "message": "Auto mode configuration updated"
    }


@router.get("/features")
async def get_available_features(user: StorageUser = Depends(require_user)):
    """Get list of available auto mode features"""
    return {
        "features": [
            {
                "name": "auto_generate_timeline",
                "description": "Automatically extract dates and events from documents",
                "available": True
            },
            {
                "name": "auto_generate_calendar",
                "description": "Create calendar events from timeline and deadlines",
                "available": True
            },
            {
                "name": "auto_identify_complaints",
                "description": "Identify agencies for filing complaints",
                "available": True
            },
            {
                "name": "auto_assess_rights",
                "description": "Automatically assess tenant rights and protections",
                "available": True
            },
            {
                "name": "auto_detect_missteps",
                "description": "Detect legal missteps and procedural violations",
                "available": True
            },
            {
                "name": "auto_suggest_tactics",
                "description": "Suggest proactive defense tactics",
                "available": True
            }
        ]
    }


@router.get("/analysis/{doc_id}")
async def get_analysis_summary(doc_id: str, user: StorageUser = Depends(require_user)):
    """Get comprehensive analysis summary for a document"""
    # TODO: Retrieve from database
    return {
        "status": "analysis_not_found",
        "message": "Please wait for analysis to complete"
    }


@router.post("/run-analysis/{doc_id}")
async def run_analysis_on_document(
    doc_id: str,
    document_content: str,
    filename: str = "document",
    user: StorageUser = Depends(require_user)
):
    """Trigger auto mode analysis on a document"""
    from app.services.auto_mode_orchestrator import AutoModeOrchestrator
    
    orchestrator = AutoModeOrchestrator()
    
    try:
        results = await orchestrator.run_full_auto_analysis(
            doc_id=doc_id,
            user_id=user.sub,
            document_content=document_content,
            filename=filename,
            document_metadata={"uploaded_by": user.sub}
        )
        
        return {
            "status": "success",
            "analysis": results.get('summary'),
            "progress": results.get('summary', {}).get('progress', 0),
            "confidence": results.get('summary', {}).get('confidence', 0),
            "recommended_actions": results.get('summary', {}).get('recommended_actions', []),
            "urgent_actions": results.get('summary', {}).get('urgent_actions', []),
            "next_steps": results.get('summary', {}).get('next_steps', [])
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/batch-analysis")
async def run_batch_analysis(
    limit: int = 5,
    user: StorageUser = Depends(require_user)
):
    """
    Run auto mode analysis on all existing uploaded documents.
    Returns aggregated summary with all findings.
    """
    import asyncio
    from pathlib import Path
    import PyPDF2
    from app.services.auto_mode_orchestrator import AutoModeOrchestrator
    
    documents_root = Path("data/documents")
    if not documents_root.exists():
        return {"status": "error", "error": "No documents folder found"}
    
    # Collect documents
    documents = []
    for user_folder in sorted(documents_root.iterdir()):
        if user_folder.is_dir() and user_folder.name != 'open-mode-user':
            user_id = user_folder.name
            for doc_file in sorted(user_folder.iterdir())[:limit]:
                if doc_file.is_file() and not doc_file.name.startswith('.'):
                    documents.append({
                        'doc_id': doc_file.stem[:20],
                        'user_id': user_id,
                        'filename': doc_file.name,
                        'filepath': str(doc_file),
                        'size': doc_file.stat().st_size
                    })
    
    if not documents:
        return {"status": "error", "error": "No documents found"}
    
    # Process documents
    async def analyze_doc(doc_info):
        try:
            # Extract text from file
            content = await _extract_text(doc_info['filepath'])
            
            if not content or len(content.strip()) < 100:
                return {'status': 'skipped', **doc_info}
            
            # Run analysis
            orchestrator = AutoModeOrchestrator()
            results = await orchestrator.run_full_auto_analysis(
                doc_id=doc_info['doc_id'],
                user_id=doc_info['user_id'],
                document_content=content,
                filename=doc_info['filename'],
                document_metadata={'uploaded_by': doc_info['user_id']}
            )
            
            return {'status': 'complete', **doc_info, 'analysis': results}
        except Exception as e:
            return {'status': 'error', 'error': str(e), **doc_info}
    
    async def _extract_text(filepath):
        """Extract text from file."""
        try:
            if filepath.lower().endswith('.pdf'):
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in list(reader.pages)[:5]:
                        text += page.extract_text() + "\n"
                    return text
            else:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()[:10000]  # First 10k chars
        except:
            return ""
    
    # Run analysis
    tasks = [analyze_doc(doc) for doc in documents[:limit]]
    results = await asyncio.gather(*tasks)
    
    # Aggregate results
    completed = sum(1 for r in results if r['status'] == 'complete')
    
    totals = {
        'timeline_events': 0,
        'calendar_events': 0,
        'complaints': 0,
        'rights': 0,
        'missteps': 0,
        'tactics': 0
    }
    
    all_actions = []
    all_urgent = []
    doc_summaries = []
    
    for result in results:
        if result['status'] == 'complete':
            summary = result.get('analysis', {}).get('summary', {})
            totals['timeline_events'] += summary.get('timeline_events', 0)
            totals['calendar_events'] += summary.get('calendar_events', 0)
            totals['complaints'] += summary.get('complaints_identified', 0)
            totals['rights'] += summary.get('rights_count', 0)
            totals['missteps'] += summary.get('missteps_count', 0)
            totals['tactics'] += summary.get('tactics_recommended', 0)
            
            all_actions.extend(summary.get('recommended_actions', []))
            all_urgent.extend(summary.get('urgent_actions', []))
            
            doc_summaries.append({
                'filename': result['filename'],
                'progress': summary.get('overall_progress', 0),
                'confidence': summary.get('analysis_confidence', 0),
                'events': summary.get('timeline_events', 0),
                'urgent_count': len(summary.get('urgent_actions', []))
            })
    
    # Sort by priority
    all_urgent.sort(key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}.get(x.get('severity', 'medium'), 3))
    all_actions.sort(key=lambda x: {'critical': 0, 'high': 1, 'medium': 2}.get(x.get('priority', 'medium'), 3))
    
    return {
        "status": "complete",
        "batch_summary": {
            "total_documents": len(documents),
            "completed": completed,
            "failed": sum(1 for r in results if r['status'] == 'error'),
            "skipped": sum(1 for r in results if r['status'] == 'skipped')
        },
        "aggregated_statistics": totals,
        "urgent_actions": all_urgent[:5],
        "recommended_actions": all_actions[:5],
        "documents": doc_summaries
    }