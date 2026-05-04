"""
Manager Dashboard Service
========================

Query functions and data aggregation for the Manager/Agency dashboard.

Provides:
- Case statistics and overview
- Staff presence and assignment tracking
- Pending signatures and documents
- Organization-wide activity feed
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.core.utc import utc_now
from app.models.models import User, InviteCode, Document


def get_dashboard_stats(
    organization_id: str,
    db_session
) -> Dict[str, Any]:
    """
    Get high-level statistics for manager dashboard.
    
    Args:
        organization_id: Organization identifier (from manager's user_id prefix)
        db_session: SQLAlchemy session
        
    Returns:
        Dictionary with stats counters
    """
    # Get all users in this organization
    org_users = db_session.query(User).filter(
        User.id.like(f"{organization_id}%")
    ).all()
    
    user_ids = [u.id for u in org_users]
    
    # Count cases (users with documents are considered active cases)
    total_cases = len(org_users)
    
    # New cases this week
    week_ago = utc_now() - timedelta(days=7)
    new_cases = db_session.query(User).filter(
        User.id.like(f"{organization_id}%"),
        User.created_at >= week_ago
    ).count()
    
    # Pending signatures (documents that need signature)
    # This is a placeholder - in production, query signature tracking table
    pending_docs = db_session.query(Document).filter(
        Document.user_id.in_(user_ids),
        Document.requires_signature == True,
        Document.signature_received == False
    ).count() if hasattr(Document, 'requires_signature') else 0
    
    # Urgent (overdue) items
    urgent_items = db_session.query(Document).filter(
        Document.user_id.in_(user_ids),
        Document.due_date < utc_now(),
        Document.completed == False
    ).count() if hasattr(Document, 'due_date') else 0
    
    return {
        "total_cases": total_cases,
        "new_cases_this_week": new_cases,
        "pending_documents": pending_docs,
        "urgent_documents": urgent_items,
        "active_staff": 0,  # TODO: Implement staff presence tracking
        "total_staff": 0,   # TODO: Implement staff counting
        "overdue_tasks": urgent_items,
    }


def get_recent_cases(
    organization_id: str,
    db_session,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get recent cases for the organization.
    
    Args:
        organization_id: Organization identifier
        db_session: SQLAlchemy session
        limit: Maximum number of cases to return
        
    Returns:
        List of case dictionaries
    """
    users = db_session.query(User).filter(
        User.id.like(f"{organization_id}%")
    ).order_by(User.created_at.desc()).limit(limit).all()
    
    cases = []
    for user in users:
        # Get latest document count as a proxy for activity
        doc_count = db_session.query(Document).filter(
            Document.user_id == user.id
        ).count()
        
        cases.append({
            "tenant_name": user.email or f"Tenant {user.id[:8]}",
            "property": "Unknown Property",  # TODO: Add property field to User
            "assigned_to": "Unassigned",  # TODO: Add case assignment
            "status": "active" if doc_count > 0 else "pending",
            "last_activity": user.updated_at.isoformat() if user.updated_at else None,
        })
    
    return cases


def get_staff_list(
    organization_id: str,
    db_session
) -> List[Dict[str, Any]]:
    """
    Get staff members for the organization.
    
    Args:
        organization_id: Organization identifier
        db_session: SQLAlchemy session
        
    Returns:
        List of staff member dictionaries
    """
    # Query users who redeemed invite codes from this organization
    redeemed_codes = db_session.query(InviteCode).filter(
        InviteCode.organization_id == organization_id,
        InviteCode.used_by.isnot(None)
    ).all()
    
    staff = []
    for code in redeemed_codes:
        if code.used_by:
            for user_id in code.used_by:
                user = db_session.query(User).filter_by(id=user_id).first()
                if user:
                    staff.append({
                        "name": user.email or f"User {user_id[:8]}",
                        "role": code.role,
                        "status": "offline",  # TODO: Implement presence tracking
                        "last_seen": user.last_login.isoformat() if user.last_login else None,
                    })
    
    return staff


def get_pending_signatures(
    organization_id: str,
    db_session
) -> List[Dict[str, Any]]:
    """
    Get documents pending signature for organization cases.
    
    Args:
        organization_id: Organization identifier
        db_session: SQLAlchemy session
        
    Returns:
        List of pending signature dictionaries
    """
    # Get organization users
    org_users = db_session.query(User).filter(
        User.id.like(f"{organization_id}%")
    ).all()
    
    user_ids = [u.id for u in org_users]
    
    # Query pending documents
    # This is a placeholder - in production, query actual signature tracking
    pending = []
    
    if hasattr(Document, 'requires_signature'):
        docs = db_session.query(Document).filter(
            Document.user_id.in_(user_ids),
            Document.requires_signature == True,
            Document.signature_received == False
        ).order_by(Document.created_at.desc()).limit(10).all()
        
        for doc in docs:
            user = db_session.query(User).filter_by(id=doc.user_id).first()
            pending.append({
                "tenant_name": user.email if user else "Unknown",
                "document_name": doc.filename or "Untitled Document",
                "due_date": doc.due_date.isoformat() if hasattr(doc, 'due_date') and doc.due_date else None,
                "sent_date": doc.created_at.isoformat() if doc.created_at else None,
            })
    
    return pending


def get_recent_activity(
    organization_id: str,
    db_session,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get recent activity feed for the organization.
    
    Args:
        organization_id: Organization identifier
        db_session: SQLAlchemy session
        limit: Maximum number of activities
        
    Returns:
        List of activity dictionaries
    """
    org_users = db_session.query(User).filter(
        User.id.like(f"{organization_id}%")
    ).all()
    
    user_ids = [u.id for u in org_users]
    
    activities = []
    
    # Recent document uploads
    recent_docs = db_session.query(Document).filter(
        Document.user_id.in_(user_ids)
    ).order_by(Document.created_at.desc()).limit(limit).all()
    
    for doc in recent_docs:
        user = db_session.query(User).filter_by(id=doc.user_id).first()
        activities.append({
            "icon": "📄",
            "description": f"<strong>{user.email or 'Tenant'}</strong> uploaded {doc.filename or 'a document'}",
            "time": format_time_ago(doc.created_at),
            "timestamp": doc.created_at.isoformat() if doc.created_at else None,
        })
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return activities[:limit]


def format_time_ago(dt: Optional[datetime]) -> str:
    """
    Format a datetime as a human-readable 'time ago' string.
    
    Args:
        dt: Datetime to format
        
    Returns:
        Human-readable time string
    """
    if not dt:
        return "Unknown"
    
    now = utc_now()
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")


def get_organization_info(
    manager_user_id: str,
    db_session
) -> Dict[str, Any]:
    """
    Get organization info for a manager.
    
    Args:
        manager_user_id: Manager's user ID
        db_session: SQLAlchemy session
        
    Returns:
        Organization info dictionary
    """
    manager = db_session.query(User).filter_by(id=manager_user_id).first()
    
    # Use first part of user ID as organization ID
    org_id = manager_user_id[:12]
    
    return {
        "id": org_id,
        "name": manager.display_name if manager else "Unknown Organization",
        "manager_id": manager_user_id,
    }
