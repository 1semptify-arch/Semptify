"""
Route Guards — Static Page Protection
======================================

Auth decorators and middleware for protecting static HTML pages.
Integrates with PageContracts to enforce role-based access.
"""

from __future__ import annotations

import functools
import logging
from typing import Optional, List, Callable, Any
from enum import Enum, auto
from dataclasses import dataclass

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse

try:
    from app.core.page_contracts import PAGE_CONTRACTS, UserRole
except ImportError:
    import sys
    sys.path.insert(0, r"c:\Semptify\Semptify-FastAPI")
    from app.core.page_contracts import PAGE_CONTRACTS, UserRole

logger = logging.getLogger(__name__)


class GuardResult(Enum):
    """Result of a guard check."""
    ALLOW = auto()
    DENY = auto()
    REDIRECT = auto()


@dataclass
class GuardCheck:
    """Result of a guard authorization check."""
    result: GuardResult
    reason: str
    redirect_url: Optional[str] = None
    status_code: int = 200


class RouteGuard:
    """
    Guard for protecting routes based on PageContracts.
    
    Usage:
        @app.get("/dashboard")
        @guard.require_auth()  # Any authenticated user
        async def dashboard():
            return FileResponse("static/dashboard.html")
        
        @app.get("/admin")
        @guard.require_roles([UserRole.ADMIN])  # Admin only
        async def admin():
            return FileResponse("static/admin.html")
    """
    
    def __init__(self):
        self._bypass_in_dev = False
        self._login_url = "/login"
        self._unauthorized_url = "/unauthorized"
    
    def configure(
        self,
        login_url: str = "/login",
        unauthorized_url: str = "/unauthorized",
        bypass_in_dev: bool = False,
    ) -> None:
        """Configure guard behavior."""
        self._login_url = login_url
        self._unauthorized_url = unauthorized_url
        self._bypass_in_dev = bypass_in_dev
    
    def _get_session_user(self, request: Request) -> Optional[dict]:
        """Extract user from session. Override for custom auth."""
        # Default: check for session-based auth
        # In production, integrate with your auth system
        session = getattr(request.state, "user", None)
        if session:
            return session
        
        # Check for JWT/Token in headers
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Validate token and return user
            return {"id": "token_user", "roles": [UserRole.USER.value]}
        
        return None
    
    def _check_contract_access(
        self,
        page_id: str,
        user: Optional[dict],
    ) -> GuardCheck:
        """Check if user can access page based on PageContract."""
        contract = PAGE_CONTRACTS.get(page_id)
        if not contract:
            # No contract = public page
            return GuardCheck(GuardResult.ALLOW, "No contract, public access")
        
        # Check if any role required
        if not contract.roles_supported or UserRole.ANONYMOUS in contract.roles_supported:
            return GuardCheck(GuardResult.ALLOW, "Anonymous allowed")
        
        # Must be authenticated
        if user is None:
            return GuardCheck(
                GuardResult.REDIRECT,
                "Authentication required",
                redirect_url=self._login_url,
            )
        
        # Check role membership
        user_roles = user.get("roles", [])
        if not isinstance(user_roles, list):
            user_roles = [user_roles]
        
        # Convert string roles to enum
        user_role_enums = []
        for role_str in user_roles:
            try:
                user_role_enums.append(UserRole(role_str))
            except ValueError:
                pass
        
        # Check if any user role is supported
        for role in user_role_enums:
            if role in contract.roles_supported:
                return GuardCheck(
                    GuardResult.ALLOW,
                    f"Role {role.value} matches contract"
                )
        
        # User authenticated but wrong role
        return GuardCheck(
            GuardResult.REDIRECT,
            f"User roles {user_roles} not in {contract.roles_supported}",
            redirect_url=self._unauthorized_url,
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    def require_auth(
        self,
        page_id: Optional[str] = None,
        redirect: bool = True,
    ) -> Callable:
        """
        Decorator: Require any authentication.
        
        Args:
            page_id: Page contract ID (auto-detected from route if None)
            redirect: If True, redirect to login; else return 401
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request from args (FastAPI injects it)
                request: Optional[Request] = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                # Check kwargs too
                if request is None:
                    request = kwargs.get("request")
                
                if request is None:
                    logger.error(f"Guard could not find request in {func.__name__}")
                    raise HTTPException(status_code=500, detail="Guard error")
                
                # Determine page_id
                check_page_id = page_id or self._infer_page_id(request)
                
                # Get user
                user = self._get_session_user(request)
                
                # Check access
                check = self._check_contract_access(check_page_id, user)
                
                if check.result == GuardResult.ALLOW:
                    return await func(*args, **kwargs)
                
                if check.result == GuardResult.REDIRECT and redirect:
                    return RedirectResponse(
                        url=check.redirect_url or self._login_url,
                        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    )
                
                # Deny with error
                raise HTTPException(
                    status_code=check.status_code or status.HTTP_401_UNAUTHORIZED,
                    detail=check.reason,
                )
            
            # Mark as guarded
            wrapper._is_guarded = True
            wrapper._page_id = page_id
            return wrapper
        return decorator
    
    def require_roles(
        self,
        roles: List[UserRole],
        page_id: Optional[str] = None,
    ) -> Callable:
        """
        Decorator: Require specific roles.
        
        Args:
            roles: List of allowed roles
            page_id: Page contract ID (auto-detected from route if None)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                request: Optional[Request] = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                if request is None:
                    request = kwargs.get("request")
                
                if request is None:
                    raise HTTPException(status_code=500, detail="Guard error")
                
                user = self._get_session_user(request)
                
                if user is None:
                    return RedirectResponse(url=self._login_url)
                
                user_roles = user.get("roles", [])
                if not isinstance(user_roles, list):
                    user_roles = [user_roles]
                
                # Check if user has any required role
                allowed_role_values = [r.value for r in roles]
                if not any(r in allowed_role_values for r in user_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required roles: {[r.value for r in roles]}"
                    )
                
                return await func(*args, **kwargs)
            
            wrapper._is_guarded = True
            wrapper._page_id = page_id
            wrapper._required_roles = roles
            return wrapper
        return decorator
    
    def _infer_page_id(self, request: Request) -> str:
        """Infer page_id from request path."""
        path = request.url.path.strip("/")
        # Remove leading slash and convert
        return path.replace("-", "_").replace("/", "_") or "index"


# Global guard instance
guard = RouteGuard()


# =============================================================================
# MIDDLEWARE
# =============================================================================

class GuardMiddleware:
    """
    ASGI middleware for automatic route protection.
    Applies guards based on PageContracts without decorator.
    """
    
    def __init__(self, app, protected_paths: Optional[List[str]] = None):
        self.app = app
        self.protected_paths = protected_paths or []
        self._guard = RouteGuard()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        path = scope.get("path", "")
        
        # Check if path is protected
        is_protected = any(
            path.startswith(p) or path == p
            for p in self.protected_paths
        )
        
        if not is_protected:
            await self.app(scope, receive, send)
            return
        
        # Check contract for this path
        page_id = path.strip("/").replace("-", "_") or "index"
        
        # For now, let request through (guard decorator handles auth)
        # Future: integrate session extraction from scope
        await self.app(scope, receive, send)


# =============================================================================
# FASTAPI INTEGRATION
# =============================================================================

def setup_guarded_routes(app, page_manifest: dict):
    """
    Automatically setup guarded routes from page manifest.
    
    Args:
        app: FastAPI app instance
        page_manifest: Dict of page_id → route info
    """
    from fastapi.responses import FileResponse
    
    for page_id, info in page_manifest.items():
        route = info.get("route", f"/{page_id.replace('_', '-')}")
        source_file = info.get("source_file", f"static/{page_id}.html")
        contract = PAGE_CONTRACTS.get(page_id)
        
        if not contract:
            # No contract = public route
            @app.get(route)
            async def public_page(path=source_file):
                return FileResponse(path)
            continue
        
        # Protected route based on contract
        if UserRole.ANONYMOUS in contract.roles_supported:
            @app.get(route)
            async def anonymous_page(path=source_file):
                return FileResponse(path)
        else:
            @app.get(route)
            @guard.require_auth(page_id=page_id)
            async def protected_page(request: Request, path=source_file):
                return FileResponse(path)


# =============================================================================
# CLI / DEBUG
# =============================================================================

if __name__ == "__main__":
    print("=== Route Guard System ===")
    print(f"Page contracts loaded: {len(PAGE_CONTRACTS)}")
    
    # Check high-priority pages
    from app.core.page_manifest import get_high_priority_pages
    
    high_priority = get_high_priority_pages()
    print(f"\nHigh priority pages: {len(high_priority)}")
    
    for page in high_priority:
        contract = PAGE_CONTRACTS.get(page.page_id)
        if contract:
            roles = [r.value for r in contract.roles_supported]
            print(f"  ✓ {page.page_id}: roles={roles}")
        else:
            print(f"  ✗ {page.page_id}: NO CONTRACT")
    
    print(f"\nGuard ready for integration with FastAPI routers.")
