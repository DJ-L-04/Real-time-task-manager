# app/models/workspace.py

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
import enum

from app.db.base import Base


class WorkspaceRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Workspace(Base):
    """
    Top-level container. Everything lives inside a workspace.
    Think of it as a company or team namespace.
    """
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("WorkspaceMember", back_populates="workspace")
    boards = relationship("Board", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    """
    Association table linking users to workspaces with a role.
    This is the RBAC (Role-Based Access Control) foundation.
    A user can be Admin in workspace A but Viewer in workspace B.
    """
    __tablename__ = "workspace_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(Enum(WorkspaceRole), default=WorkspaceRole.MEMBER)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")


class Board(Base):
    """
    A board lives inside a workspace. Like a Trello board.
    Has multiple columns (To Do, In Progress, Done).
    """
    __tablename__ = "boards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="boards")
    columns = relationship("BoardColumn", back_populates="board", cascade="all, delete-orphan",
                           order_by="BoardColumn.position")


class BoardColumn(Base):
    """
    A column inside a board. Has a position for ordering.
    cascade="all, delete-orphan" means deleting a column deletes its tasks.
    """
    __tablename__ = "board_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id = Column(UUID(as_uuid=True), ForeignKey("boards.id"), nullable=False)
    name = Column(String, nullable=False)
    position = Column(Integer, default=0)  # for ordering columns left to right
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    board = relationship("Board", back_populates="columns")
    tasks = relationship("Task", back_populates="column", cascade="all, delete-orphan",
                         order_by="Task.position")
