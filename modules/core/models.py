"""
Core Module Models

Database models for core functionality.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

Base = declarative_base()

class SystemLog(Base):
    """System logging - for debugging system issues only"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)  # INFO, ERROR, WARNING, DEBUG
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON)  # Additional structured data
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<SystemLog(level='{self.level}', module='{self.module}')>"

class SystemConfig(Base):
    """System configuration"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemConfig(key='{self.key}')>"

class UserSession(Base):
    """User session management"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)

    def __repr__(self):
        return f"<UserSession(user_id='{self.user_id}', session_id='{self.session_id[:8]}...')>"

# Pydantic Models
class SystemLogCreate(BaseModel):
    """Create system log entry"""
    level: str
    module: str
    message: str
    data: Optional[Dict[str, Any]] = None

class SystemLogResponse(BaseModel):
    """System log response"""
    id: int
    level: str
    module: str
    message: str
    data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class SystemConfigUpdate(BaseModel):
    """Update system configuration"""
    key: str
    value: Any
    description: Optional[str] = None

class SystemConfigResponse(BaseModel):
    """System configuration response"""
    id: int
    key: str
    value: Any
    description: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]
    system: Dict[str, Any]

class SystemStatusResponse(BaseModel):
    """System status response"""
    application: Dict[str, str]
    database: Dict[str, str]
    cache: Dict[str, str]
    modules: list[str]

# Utility functions
def create_system_log(level: str, module: str, message: str, data: Optional[Dict] = None) -> SystemLog:
    """Create a system log entry"""
    return SystemLog(
        level=level.upper(),
        module=module,
        message=message,
        data=data
    )

def get_log_level_value(level: str) -> int:
    """Get numeric value for log level"""
    levels = {
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50
    }
    return levels.get(level.upper(), 20)