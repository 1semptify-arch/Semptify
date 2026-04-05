"""
Fix for OAuth State Persistence
Apply this to improve production stability
"""

# 1. ADD THIS MODEL to app/models/__init__.py or app/models/storage.py

from sqlalchemy import Column, String, JSON, DateTime, delete
from sqlalchemy.orm import declarative_base
from datetime import datetime, timedelta
import json

class OAuthState(Base):
    """Persistent OAuth state storage (replaces in-memory dict)"""
    __tablename__ = "oauth_states"
    
    id = Column(String(255), primary_key=True)  # state token
    provider = Column(String(50), nullable=False)
    role = Column(String(50), nullable=True)
    existing_uid = Column(String(255), nullable=True)
    return_to = Column(String(512), nullable=True)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# 2. UPDATE app/routers/storage.py - Replace the in-memory storage

# BEFORE (lines 80-94):
# OAUTH_STATES: dict[str, dict] = {}
# OAUTH_STATE_TIMEOUT_MINUTES = 15
# def _cleanup_expired_states(): ...

# AFTER (replace with this):

from app.models import OAuthState
from sqlalchemy import and_

OAUTH_STATE_TIMEOUT_MINUTES = 15

async def _cleanup_expired_states(db: AsyncSession):
    """Remove expired OAuth states from database."""
    result = await db.execute(
        delete(OAuthState).where(
            OAuthState.expires_at < datetime.utcnow()
        )
    )
    if result.rowcount > 0:
        print(f"🧹 Cleaned up {result.rowcount} expired OAuth states")
    await db.commit()


# 3. UPDATE STATE GENERATION (around line 968)

# BEFORE:
# state = secrets.token_urlsafe(32)
# OAUTH_STATES[state] = { ... }

# AFTER:
async def initiate_oauth(
    provider: str, 
    request: Request,
    db: AsyncSession = Depends(get_db),  # ADD THIS
    ...
):
    # Generate state
    state = secrets.token_urlsafe(32)
    
    # Store in database instead of dict
    oauth_state = OAuthState(
        id=state,
        provider=provider,
        role=role,
        existing_uid=existing_uid,
        return_to=return_to,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=OAUTH_STATE_TIMEOUT_MINUTES)
    )
    db.add(oauth_state)
    await db.commit()
    
    # Rest of function same...


# 4. UPDATE CALLBACK VALIDATION (around line 1035)

# BEFORE:
# if state not in OAUTH_STATES:
#     raise HTTPException(...)
# state_data = OAUTH_STATES.pop(state)

# AFTER:
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ...
):
    await _cleanup_expired_states(db)
    
    # Query database instead of dict
    result = await db.execute(
        select(OAuthState).where(OAuthState.id == state)
    )
    state_record = result.scalar_one_or_none()
    
    if not state_record:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "message": "Invalid or expired state. Please try connecting your storage again.",
                "action": "redirect",
                "redirect_url": "/storage/providers"
            }
        )
    
    if state_record.is_expired():
        await db.delete(state_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="State expired")
    
    if state_record.provider != provider:
        raise HTTPException(status_code=400, detail="Provider mismatch")
    
    # Extract data
    state_data = {
        "provider": state_record.provider,
        "role": state_record.role,
        "existing_uid": state_record.existing_uid,
        "return_to": state_record.return_to,
    }
    
    # Clean up used state
    await db.delete(state_record)
    await db.commit()
    
    # Rest of function same...
