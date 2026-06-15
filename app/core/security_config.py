"""
Production Security Configuration
Enforced security settings for production deployment
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import logging
logger = logging.getLogger(__name__)

class SecuritySettings(BaseSettings):
    """Production security configuration"""

    # Read production-specific overrides first, then fall back to shared .env.
    # Ignore unrelated env keys that belong to other app subsystems.
    model_config = SettingsConfigDict(
        env_file=(".env.production", ".env"),
        case_sensitive=True,
        extra="ignore",
    )
    
    # Environment
    ENVIRONMENT: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    
    # API Security
    API_KEY: str = Field(default="")
    SECRET_KEY: str = Field(default="change-me-in-production")
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=os.getenv("CORS_ORIGINS", "https://localhost:8443,https://semptify.local").split(",")
    )
    ALLOW_CREDENTIALS: bool = Field(default=True)
    ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    ALLOW_HEADERS: List[str] = Field(
        default=["Content-Type", "Authorization", "X-API-Key"]
    )
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_PERIOD: int = Field(default=60)  # seconds
    
    # Authentication
    AUTH_REQUIRED: bool = Field(default=True)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRY: int = Field(default=3600)  # seconds
    
    # HTTPS/SSL
    HTTPS_ONLY: bool = Field(default=True)
    SSL_CERT_PATH: str = Field(default="/etc/ssl/certs/cert.pem")
    SSL_KEY_PATH: str = Field(default="/etc/ssl/private/key.pem")
    
    # Security Headers
    HSTS_MAX_AGE: int = Field(default=31536000)  # 1 year
    CSP_ENABLED: bool = Field(default=True)
    
    # Database Security
    DB_SSL_MODE: str = Field(default="require")
    DB_CONNECTION_TIMEOUT: int = Field(default=10)
    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=0)
    
    # Logging & Monitoring
    LOG_LEVEL: str = Field(default="INFO")
    SENTRY_ENABLED: bool = Field(default=False)
    SENTRY_DSN: str = Field(default="")
    
    # Input Validation
    MAX_REQUEST_SIZE: int = Field(default=10 * 1024 * 1024)  # 10MB
    MAX_BATCH_DOCUMENTS: int = Field(default=100)
    
    # Session Security
    SESSION_TIMEOUT: int = Field(default=1800)  # 30 minutes
    SECURE_COOKIES: bool = Field(default=True)
    HTTPONLY_COOKIES: bool = Field(default=True)
    SAMESITE_COOKIES: str = Field(default="Strict")
    
    # Cloudflare R2 System Storage
    R2_ACCOUNT_ID: str = Field(default="")
    R2_ACCESS_KEY_ID: str = Field(default="")
    R2_SECRET_ACCESS_KEY: str = Field(default="")
    R2_BUCKET_NAME: str = Field(default="semptify-system")
    R2_ENDPOINT: str = Field(default="")
    
    # IP Whitelisting
    IP_WHITELIST_ENABLED: bool = Field(default=False)
    IP_WHITELIST: List[str] = Field(default=[])
    
    def validate_production(self) -> bool:
        """Validate production security settings"""
        if self.ENVIRONMENT == "production":
            issues = []
            
            if self.DEBUG:
                issues.append("DEBUG mode is enabled in production")
            
            if self.SECRET_KEY == "change-me-in-production":
                issues.append("SECRET_KEY not changed from default")
            
            if len(self.ALLOWED_ORIGINS) == 0:
                issues.append("No allowed origins configured")
            
            if not self.HTTPS_ONLY:
                issues.append("HTTPS not enforced")
            
            if not self.AUTH_REQUIRED:
                issues.append("Authentication not required")
            
            if not self.RATE_LIMIT_ENABLED:
                issues.append("Rate limiting not enabled")
            
            if issues:
                raise ValueError(f"Production security issues: {', '.join(issues)}")
        
        return True

def get_security_settings() -> SecuritySettings:
    """Get security settings instance"""
    return SecuritySettings()
