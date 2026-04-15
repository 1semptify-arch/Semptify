"""
Production Mode Initialization
Validate and enforce security on startup
"""

import os
import sys
import logging
from pathlib import Path

from app.core.security_config import get_security_settings, SecuritySettings

logger = logging.getLogger(__name__)

def validate_production_mode() -> bool:
    """Validate production mode is properly configured"""
    
    try:
        settings = get_security_settings()
        
        logger.info("=" * 70)
        logger.info("PRODUCTION MODE VALIDATION")
        logger.info("=" * 70)
        
        # Environment
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug Mode: {settings.DEBUG}")
        
        if settings.ENVIRONMENT == "production":
            # Critical checks
            logger.info("\n🔐 SECURITY CHECKS:")
            
            # 1. Debug mode
            if settings.DEBUG:
                logger.error("❌ DEBUG mode is ENABLED in production!")
                return False
            logger.info("✅ Debug mode disabled")
            
            # 2. Secret key
            if settings.SECRET_KEY == "change-me-in-production":
                logger.error("❌ SECRET_KEY not changed from default!")
                return False
            logger.info("✅ Secret key configured")
            
            # 3. HTTPS enforcement
            if not settings.HTTPS_ONLY:
                logger.error("❌ HTTPS NOT enforced!")
                return False
            logger.info("✅ HTTPS enforced")
            
            # 4. Authentication
            if not settings.AUTH_REQUIRED:
                logger.error("❌ Authentication NOT required!")
                return False
            logger.info("✅ Authentication required")
            
            # 5. Rate limiting
            if not settings.RATE_LIMIT_ENABLED:
                logger.error("❌ Rate limiting NOT enabled!")
                return False
            logger.info(f"✅ Rate limiting enabled ({settings.RATE_LIMIT_REQUESTS} req/{settings.RATE_LIMIT_PERIOD}s)")
            
            # 6. CORS
            if len(settings.ALLOWED_ORIGINS) == 0:
                logger.error("❌ No CORS origins configured!")
                return False
            logger.info(f"✅ CORS configured for {len(settings.ALLOWED_ORIGINS)} origins")
            
            # 7. System storage: Cloudflare R2
            missing_r2 = []
            if not settings.R2_ACCOUNT_ID:
                missing_r2.append("R2_ACCOUNT_ID")
            if not settings.R2_ACCESS_KEY_ID:
                missing_r2.append("R2_ACCESS_KEY_ID")
            if not settings.R2_SECRET_ACCESS_KEY:
                missing_r2.append("R2_SECRET_ACCESS_KEY")
            if not settings.R2_BUCKET_NAME:
                missing_r2.append("R2_BUCKET_NAME")
            if missing_r2:
                logger.error("❌ Cloudflare R2 system storage is not fully configured: %s", ", ".join(missing_r2))
                return False
            logger.info("✅ Cloudflare R2 system storage configured")
            
            # 8. Database SSL
            if settings.DB_SSL_MODE != "require":
                logger.warning("⚠️  Database SSL mode not set to 'require'")
            logger.info(f"✅ Database SSL: {settings.DB_SSL_MODE}")
            
            # 9. Secure cookies
            if not settings.SECURE_COOKIES or not settings.HTTPONLY_COOKIES:
                logger.warning("⚠️  Cookie security may not be optimal")
            logger.info(f"✅ Secure cookies: {settings.SECURE_COOKIES}, HttpOnly: {settings.HTTPONLY_COOKIES}")
            
            logger.info("\n" + "=" * 70)
            logger.info("✅ PRODUCTION MODE: ALL SECURITY CHECKS PASSED")
            logger.info("=" * 70)
            
        else:
            logger.info(f"💡 Running in {settings.ENVIRONMENT} mode")
            logger.info("Security checks relaxed for non-production environment")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Production validation failed: {str(e)}")
        return False

def setup_production_logging(settings: SecuritySettings) -> None:
    """Configure production logging"""
    
    # Create logs directory if needed
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # File handler
    file_handler = logging.FileHandler(log_dir / "production.log")
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(file_handler)
    
    # Console handler (for ERROR and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(console_handler)
    
    logger.info(f"Production logging configured to {log_dir / 'production.log'}")

def initialize_production_mode() -> bool:
    """Initialize production mode"""
    
    try:
        settings = get_security_settings()
        setup_production_logging(settings)
        return validate_production_mode()
    except Exception as e:
        logger.error(f"Failed to initialize production mode: {str(e)}")
        return False
