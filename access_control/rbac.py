"""
FastAPI RBAC dependency factory.

Usage in endpoint handlers:

    from access_control.rbac import require_permission, require_role
    from access_control.permissions import P_SESSION_CREATE

    @app.post("/sessions")
    def create_session(
        ...,
        current_user: models.User = Depends(require_permission(P_SESSION_CREATE)),
    ):
        ...

    # Or check raw role membership:
    @app.get("/admin/users")
    def list_users(
        current_user: models.User = Depends(require_role("ADM")),
    ):
        ...
"""

from typing import Callable

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user_from_token
from backend import models
from access_control.permissions import has_permission


# ─── Base: extract + validate JWT ────────────────────────────────────────────

def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Shared dependency used by all protected endpoints.
    Validates the Bearer JWT and returns the active User.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — provide a Bearer token",
        )
    token = authorization.split(" ", 1)[1]
    user = get_current_user_from_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


# ─── Guards ───────────────────────────────────────────────────────────────────

def require_permission(permission: str) -> Callable:
    """
    Returns a FastAPI dependency that checks the current user has
    the given permission.  Raises HTTP 403 if not.

    Example:
        current_user = Depends(require_permission(P_SESSION_CREATE))
    """
    def checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted to perform: {permission}",
            )
        return current_user
    return checker


def require_role(*roles: str) -> Callable:
    """
    Returns a FastAPI dependency that checks the current user has
    one of the listed roles.  Raises HTTP 403 if not.

    Example:
        current_user = Depends(require_role("ADM"))
        current_user = Depends(require_role("ME", "SME"))
    """
    role_set = set(roles)

    def checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in role_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.role}' is not permitted. "
                    f"Required: {sorted(role_set)}"
                ),
            )
        return current_user
    return checker
