"""Judge module — DEPRECATED. Merged into Legal role as sub_role='judge'.

As of 2026-06-23, Judge is no longer a standalone role. It is a sub-role
of Legal (legal_sub_role='judge' on User model). This stub remains for
backward compatibility with services that reference UserRole.JUDGE.

New judge functionality should be added to the Legal module with
is_legal_sub_role(user_id, 'judge') checks.
"""

from .router import router

__all__ = ["router"]
