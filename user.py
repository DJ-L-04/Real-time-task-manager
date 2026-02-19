# app/models/user.py
#
# ORM models are Python classes that map directly to database tables.
# SQLAlchemy handles the SQL — you work with Python objects.
# Each Column() call maps to a column in the table.
# relationship() sets up Python-level object linking (no extra SQL needed for access).

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    # UUID primary key — more secure than auto-increment integers
    # Can't enumerate users by guessing sequential IDs
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # refresh_token stored in DB so we can invalidate on logout
    refresh_token = Column(String, nullable=True)

    # Relationships — SQLAlchemy loads related objects automatically
    workspace_memberships = relationship("WorkspaceMember", back_populates="user")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    activities = relationship("ActivityLog", back_populates="user")
