"""
Production Security Configuration
Enforced security settings for production deployment
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API Security
    API_KEY: str = Field(default="", env="API_KEY")
    SECRET_KEY: str = Field(default="change-me-in-production", env="SECRET_KEY")
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["https://localhost:8443", "https://semptify.local"],
        env="ALLOWED_ORIGINS"
    )
    ALLOW_CREDENTIALS: bool = Field(default=True, env="ALLOW_CREDENTIALS")
    ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="ALLOW_METHODS"
    )
    ALLOW_HEADERS: List[str] = Field(
        default=["Content-Type", "Authorization", "X-API-Key"],
        env="ALLOW_HEADERS"
    )
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds
    
    # Authentication
    AUTH_REQUIRED: bool = Field(default=True, env="AUTH_REQUIRED")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRY: int = Field(default=3600, env="JWT_EXPIRY")  # seconds
    
    # HTTPS/SSL
    HTTPS_ONLY: bool = Field(default=True, env="HTTPS_ONLY")
    SSL_CERT_PATH: str = Field(default="/etc/ssl/certs/cert.pem", env="SSL_CERT_PATH")
    SSL_KEY_PATH: str = Field(default="/etc/ssl/private/key.pem", env="SSL_KEY_PATH")
    
    # Security Headers
    HSTS_MAX_AGE: int = Field(default=31536000, env="HSTS_MAX_AGE")  # 1 year
    CSP_ENABLED: bool = Field(default=True, env="CSP_ENABLED")
    
    # Database Security
    DB_SSL_MODE: str = Field(default="require", env="DB_SSL_MODE")
    DB_CONNECTION_TIMEOUT: int = Field(default=10, env="DB_CONNECTION_TIMEOUT")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=0, env="DB_MAX_OVERFLOW")
    
    # Logging & Monitoring
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    SENTRY_ENABLED: bool = Field(default=False, env="SENTRY_ENABLED")
    SENTRY_DSN: str = Field(default="", env="SENTRY_DSN")
    
    # Input Validation
    MAX_REQUEST_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_REQUEST_SIZE")  # 10MB
    MAX_BATCH_DOCUMENTS: int = Field(default=100, env="MAX_BATCH_DOCUMENTS")
    
    # Session Security
    SESSION_TIMEOUT: int = Field(default=1800, env="SESSION_TIMEOUT")  # 30 minutes
    SECURE_COOKIES: bool = Field(default=True, env="SECURE_COOKIES")
    HTTPONLY_COOKIES: bool = Field(default=True, env="HTTPONLY_COOKIES")
    SAMESITE_COOKIES: str = Field(default="Strict", env="SAMESITE_COOKIES")
    
    # Cloudflare R2 System Storage
    R2_ACCOUNT_ID: str = Field(default="", env="R2_ACCOUNT_ID")
    R2_ACCESS_KEY_ID: str = Field(default="", env="R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY: str = Field(default="", env="R2_SECRET_ACCESS_KEY")
    R2_BUCKET_NAME: str = Field(default="semptify-system", env="R2_BUCKET_NAME")
    R2_ENDPOINT: str = Field(default="", env="R2_ENDPOINT")
    
    # IP Whitelisting
    IP_WHITELIST_ENABLED: bool = Field(default=False, env="IP_WHITELIST_ENABLED")
    IP_WHITELIST: List[str] = Field(default=[], env="IP_WHITELIST")
    
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
