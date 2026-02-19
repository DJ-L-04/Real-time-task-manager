# app/core/dependencies.py
#
# Dependencies are reusable functions FastAPI injects into endpoints.
# They run BEFORE your endpoint function executes.
#
# Flow for a protected endpoint:
# Request → get_current_user (validates JWT) → require_workspace_role (checks RBAC) → endpoint
#
# This keeps auth logic out of every single endpoint function.

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.db.base import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole

# HTTPBearer extracts the token from the Authorization: Bearer <token> header
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate JWT access token and return the current user.
    Raises 401 if token is missing, invalid, or expired.
    Injected into any endpoint that requires authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    # token type check — refresh tokens can't be used as access tokens
    if payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user or not user.is_active:
        raise credentials_exception

    return user


def get_workspace_member(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WorkspaceMember:
    """
    Verify the current user is a member of the given workspace.
    Returns the membership object (which contains their role).
    Raises 403 if they're not a member.
    """
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace"
        )
    return membership


def require_admin(membership: WorkspaceMember = Depends(get_workspace_member)) -> WorkspaceMember:
    """
    Require Admin role for workspace-level operations.
    (Adding members, deleting boards, etc.)
    Usage: membership = Depends(require_admin)
    """
    if membership.role != WorkspaceRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return membership


def require_member_or_above(
    membership: WorkspaceMember = Depends(get_workspace_member)
) -> WorkspaceMember:
    """
    Allow Admin and Member roles (not Viewer) for write operations.
    Viewers can read but not create/update/delete tasks.
    """
    if membership.role == WorkspaceRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member or Admin role required to perform this action"
        )
    return membership
