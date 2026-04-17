"""
Centralized Error Handling System
================================

Provides consistent error responses and user feedback across the application.
"""

import logging
import traceback
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class SemptifyError(Exception):
    """Base exception for Semptify application errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "GENERAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or "An error occurred. Please try again."
        super().__init__(self.message)

class UserError(SemptifyError):
    """Error caused by user input or actions."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "USER_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            user_message=user_message or "Please check your input and try again."
        )

class StorageError(SemptifyError):
    """Error related to storage operations."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "STORAGE_ERROR",
        status_code: int = 503,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            user_message=user_message or "Storage service is temporarily unavailable. Please try again later."
        )

class AuthenticationError(SemptifyError):
    """Error related to authentication or authorization."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_ERROR",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            user_message=user_message or "Authentication required. Please log in and try again."
        )

class ValidationError(SemptifyError):
    """Error related to data validation."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        status_code: int = 422,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            user_message=user_message or "Invalid data provided. Please check your input."
        )

def create_error_response(
    error: SemptifyError,
    include_details: bool = False
) -> JSONResponse:
    """Create standardized error response."""
    
    response_data = {
        "success": False,
        "error": {
            "code": error.error_code,
            "message": error.user_message,
            "timestamp": "2024-01-01T00:00:00Z"  # Will be updated
        }
    }
    
    # Include technical details in development or when explicitly requested
    if include_details or error.details:
        response_data["error"]["technical_message"] = error.message
        response_data["error"]["details"] = error.details
    
    return JSONResponse(
        status_code=error.status_code,
        content=response_data
    )

async def semptify_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for Semptify application."""
    
    # Log the error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Handle different exception types
    if isinstance(exc, SemptifyError):
        return create_error_response(exc, include_details=False)
    
    elif isinstance(exc, HTTPException):
        user_error = SemptifyError(
            message=exc.detail,
            error_code="HTTP_ERROR",
            status_code=exc.status_code,
            user_message=exc.detail
        )
        return create_error_response(user_error)
    
    elif isinstance(exc, RequestValidationError):
        validation_errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append(f"{field}: {error['msg']}")
        
        user_error = ValidationError(
            message=f"Validation failed: {', '.join(validation_errors)}",
            error_code="VALIDATION_ERROR",
            details={"validation_errors": exc.errors()},
            user_message="Invalid input data. Please check all fields and try again."
        )
        return create_error_response(user_error)
    
    elif isinstance(exc, StarletteHTTPException):
        user_error = SemptifyError(
            message=exc.detail,
            error_code="HTTP_ERROR",
            status_code=exc.status_code,
            user_message=exc.detail
        )
        return create_error_response(user_error)
    
    # Default: unknown error
    unknown_error = SemptifyError(
        message=str(exc),
        error_code="UNKNOWN_ERROR",
        status_code=500,
        details={"traceback": traceback.format_exc()},
        user_message="An unexpected error occurred. Please try again later."
    )
    
    return create_error_response(unknown_error, include_details=False)

def log_error(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """Log error with context."""
    
    log_data = {
        "error_type": error_type,
        "message": message,
        "details": details or {},
        "user_id": user_id,
        "request_id": request_id
    }
    
    logger.error(f"Semptify Error: {error_type} - {message}", extra=log_data)

def handle_component_error(
    component_name: str,
    error: Exception,
    user_message: Optional[str] = None
) -> SemptifyError:
    """Handle component-specific errors."""
    
    error_type = type(error).__name__
    log_error(
        error_type=f"COMPONENT_ERROR_{component_name.upper()}",
        message=str(error),
        details={"component": component_name, "error_type": error_type}
    )
    
    if isinstance(error, SemptifyError):
        return error
    
    return SemptifyError(
        message=f"Component {component_name} error: {str(error)}",
        error_code=f"COMPONENT_ERROR_{component_name.upper()}",
        user_message=user_message or f"The {component_name} component encountered an error. Please try again."
    )

# Error message templates for common scenarios
ERROR_MESSAGES = {
    "file_upload": {
        "size_limit": "File size exceeds the maximum allowed limit.",
        "invalid_type": "File type is not supported.",
        "corrupted": "The uploaded file appears to be corrupted.",
        "storage_full": "Storage quota exceeded. Please delete some files and try again."
    },
    "authentication": {
        "invalid_credentials": "Invalid username or password.",
        "session_expired": "Your session has expired. Please log in again.",
        "access_denied": "You don't have permission to access this resource.",
        "token_invalid": "Invalid or expired authentication token."
    },
    "storage": {
        "provider_unavailable": "Storage provider is temporarily unavailable.",
        "connection_failed": "Failed to connect to storage service.",
        "quota_exceeded": "Storage quota exceeded.",
        "file_not_found": "The requested file was not found."
    },
    "validation": {
        "required_field": "This field is required.",
        "invalid_format": "Invalid format provided.",
        "out_of_range": "Value is out of allowed range.",
        "duplicate_entry": "This entry already exists."
    }
}

def get_error_message(category: str, key: str, **kwargs) -> str:
    """Get formatted error message from templates."""
    
    if category in ERROR_MESSAGES and key in ERROR_MESSAGES[category]:
        message = ERROR_MESSAGES[category][key]
        try:
            return message.format(**kwargs)
        except KeyError:
            return message
    
    return f"Error in {category}: {key}"

# Rate limiting error handling
class RateLimitError(SemptifyError):
    """Error raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Too many requests",
        retry_after: Optional[int] = None,
        user_message: Optional[str] = None
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            user_message=user_message or f"Too many requests. Please wait {retry_after or 'a few'} seconds and try again."
        )

# Database error handling
class DatabaseError(SemptifyError):
    """Error related to database operations."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DATABASE_ERROR",
        status_code: int = 503,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            user_message=user_message or "Database service is temporarily unavailable. Please try again later."
        )

# Helper functions for common error scenarios
def handle_file_upload_error(error: Exception, filename: str) -> SemptifyError:
    """Handle file upload specific errors."""
    
    error_str = str(error).lower()
    
    if "size" in error_str or "too large" in error_str:
        return UserError(
            message=f"File size error for {filename}: {str(error)}",
            error_code="FILE_SIZE_ERROR",
            user_message=get_error_message("file_upload", "size_limit")
        )
    
    elif "type" in error_str or "format" in error_str:
        return UserError(
            message=f"File type error for {filename}: {str(error)}",
            error_code="FILE_TYPE_ERROR",
            user_message=get_error_message("file_upload", "invalid_type")
        )
    
    elif "quota" in error_str or "space" in error_str:
        return StorageError(
            message=f"Storage quota error for {filename}: {str(error)}",
            error_code="STORAGE_QUOTA_ERROR",
            user_message=get_error_message("storage", "quota_exceeded")
        )
    
    return StorageError(
        message=f"Upload error for {filename}: {str(error)}",
        error_code="UPLOAD_ERROR",
        details={"filename": filename}
    )

def handle_oauth_error(error: Exception, provider: str) -> SemptifyError:
    """Handle OAuth specific errors."""
    
    error_str = str(error).lower()
    
    if "token" in error_str and "expired" in error_str:
        return AuthenticationError(
            message=f"OAuth token expired for {provider}: {str(error)}",
            error_code="OAUTH_TOKEN_EXPIRED",
            user_message=get_error_message("authentication", "session_expired")
        )
    
    elif "access" in error_str and "denied" in error_str:
        return AuthenticationError(
            message=f"OAuth access denied for {provider}: {str(error)}",
            error_code="OAUTH_ACCESS_DENIED",
            user_message=get_error_message("authentication", "access_denied")
        )
    
    return AuthenticationError(
        message=f"OAuth error for {provider}: {str(error)}",
        error_code="OAUTH_ERROR",
        details={"provider": provider}
    )
