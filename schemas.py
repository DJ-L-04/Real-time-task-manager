# app/schemas/auth.py
#
# Pydantic schemas are the "contract" between client and server.
# They validate incoming request bodies and shape outgoing responses.
# Completely separate from ORM models — this is intentional.
# ORM models = database shape. Schemas = API shape.

from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid


class UserRegister(BaseModel):
    """Request body for POST /auth/register"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Request body for POST /auth/login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response after successful login or token refresh"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Request body for POST /auth/refresh"""
    refresh_token: str


# app/schemas/user.py
class UserResponse(BaseModel):
    """Public user data returned in API responses. Never include hashed_password."""
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True  # allows creating from SQLAlchemy ORM objects


# app/schemas/workspace.py
from datetime import datetime


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    owner_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AddMemberRequest(BaseModel):
    user_email: EmailStr
    role: str = "member"  # admin | member | viewer


# app/schemas/board.py
class BoardCreate(BaseModel):
    name: str
    description: Optional[str] = None


class BoardResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ColumnCreate(BaseModel):
    name: str
    position: int = 0


class ColumnResponse(BaseModel):
    id: uuid.UUID
    board_id: uuid.UUID
    name: str
    position: int

    class Config:
        from_attributes = True


# app/schemas/task.py
from typing import Literal


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assignee_id: Optional[uuid.UUID] = None


class TaskUpdate(BaseModel):
    """All fields optional — PATCH semantics, only update what's provided"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[uuid.UUID] = None
    column_id: Optional[uuid.UUID] = None  # for moving between columns
    position: Optional[int] = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    column_id: uuid.UUID
    title: str
    description: Optional[str]
    priority: str
    status: str
    position: int
    due_date: Optional[datetime]
    assignee_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# app/schemas/activity.py
class ActivityResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    metadata_json: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
