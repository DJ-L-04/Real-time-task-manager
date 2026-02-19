# app/api/endpoints/workspaces.py
#
# Workspace management. The dependency chain enforces RBAC:
# - Anyone authenticated can create a workspace
# - Only workspace members can view it
# - Only admins can add/remove members or delete the workspace

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.db.base import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.core.dependencies import get_current_user, get_workspace_member, require_admin
from app.schemas.schemas import WorkspaceCreate, WorkspaceResponse, AddMemberRequest, UserResponse

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("/", response_model=WorkspaceResponse, status_code=201)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a workspace. Creator automatically becomes Admin.
    We add them as a WorkspaceMember with role=ADMIN in the same transaction.
    """
    workspace = Workspace(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id
    )
    db.add(workspace)
    db.flush()  # flush to get the workspace.id without committing

    # Add creator as admin member
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=WorkspaceRole.ADMIN
    )
    db.add(membership)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("/", response_model=List[WorkspaceResponse])
def list_my_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all workspaces the current user is a member of."""
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == current_user.id
    ).all()
    workspace_ids = [m.workspace_id for m in memberships]
    return db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all()


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_workspace_member),  # verifies membership
    db: Session = Depends(get_db)
):
    """Get workspace details. Any member can view."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/{workspace_id}/members")
def add_member(
    workspace_id: uuid.UUID,
    payload: AddMemberRequest,
    membership: WorkspaceMember = Depends(require_admin),  # only admins
    db: Session = Depends(get_db)
):
    """
    Add a user to workspace by email. Only Admins can do this.
    The require_admin dependency handles the RBAC check automatically.
    """
    user_to_add = db.query(User).filter(User.email == payload.user_email).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_to_add.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")

    role_map = {"admin": WorkspaceRole.ADMIN, "member": WorkspaceRole.MEMBER, "viewer": WorkspaceRole.VIEWER}
    new_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_to_add.id,
        role=role_map.get(payload.role, WorkspaceRole.MEMBER)
    )
    db.add(new_member)
    db.commit()
    return {"message": f"Added {user_to_add.email} as {payload.role}"}


@router.delete("/{workspace_id}/members/{user_id}")
def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    membership: WorkspaceMember = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Remove a member. Only Admins can do this. Can't remove yourself."""
    if user_id == membership.user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    target = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(target)
    db.commit()
    return {"message": "Member removed"}
