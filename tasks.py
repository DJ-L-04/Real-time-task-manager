# app/api/endpoints/tasks.py
#
# Task CRUD. The critical addition here vs a basic CRUD:
# After every write operation (create/update/delete),
# we publish an event to Redis so WebSocket clients get notified in real time.
#
# Flow: Client updates task → DB updated → Redis event published → 
#       WebSocket handler receives event → broadcasts to all connected clients

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import json

from app.db.base import get_db
from app.db.redis import async_redis
from app.models.task import Task, ActivityLog, ActivityAction
from app.models.workspace import WorkspaceMember, BoardColumn, Board
from app.models.user import User
from app.core.dependencies import get_current_user, require_member_or_above
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskResponse, ActivityResponse
from app.worker.tasks import send_assignment_notification

router = APIRouter(prefix="/columns/{column_id}/tasks", tags=["Tasks"])


async def publish_task_event(workspace_id: uuid.UUID, event_type: str, task_data: dict):
    """
    Publish a task event to Redis channel for a workspace.
    Channel name: workspace:{workspace_id}
    All WebSocket clients subscribed to this channel receive the event.
    
    This is the bridge between REST operations and real-time WebSocket updates.
    """
    event = json.dumps({
        "event": event_type,  # "task_created", "task_updated", "task_deleted"
        "data": task_data
    })
    await async_redis.publish(f"workspace:{workspace_id}", event)


def get_workspace_id_for_column(column_id: uuid.UUID, db: Session) -> uuid.UUID:
    """Helper to traverse: column → board → workspace for event publishing."""
    column = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")
    board = db.query(Board).filter(Board.id == column.board_id).first()
    return board.workspace_id


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    column_id: uuid.UUID,
    payload: TaskCreate,
    membership: WorkspaceMember = Depends(require_member_or_above),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = Task(
        column_id=column_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        assignee_id=payload.assignee_id
    )
    db.add(task)
    db.flush()

    # Log the activity
    activity = ActivityLog(
        task_id=task.id,
        user_id=current_user.id,
        action=ActivityAction.CREATED
    )
    db.add(activity)
    db.commit()
    db.refresh(task)

    # Get workspace_id for pub/sub channel
    workspace_id = get_workspace_id_for_column(column_id, db)

    # Publish event to Redis — triggers real-time update for all WebSocket clients
    task_dict = {
        "id": str(task.id),
        "title": task.title,
        "column_id": str(task.column_id),
        "priority": task.priority,
        "status": task.status,
        "assignee_id": str(task.assignee_id) if task.assignee_id else None
    }
    await publish_task_event(workspace_id, "task_created", task_dict)

    # If task is assigned, send email notification via Celery (async, non-blocking)
    if task.assignee_id:
        send_assignment_notification.delay(str(task.id), str(task.assignee_id))

    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    column_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    membership: WorkspaceMember = Depends(require_member_or_above),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Track what changed for the activity log
    changes = {}
    update_data = payload.model_dump(exclude_unset=True)  # only fields explicitly set

    for field, value in update_data.items():
        old_value = getattr(task, field)
        if old_value != value:
            changes[field] = {"from": str(old_value), "to": str(value)}
            setattr(task, field, value)

    if changes:
        activity = ActivityLog(
            task_id=task.id,
            user_id=current_user.id,
            action=ActivityAction.UPDATED,
            metadata_json=json.dumps(changes)
        )
        db.add(activity)

        # If assignee changed, send notification
        if "assignee_id" in changes and task.assignee_id:
            send_assignment_notification.delay(str(task.id), str(task.assignee_id))

    db.commit()
    db.refresh(task)

    workspace_id = get_workspace_id_for_column(column_id, db)
    task_dict = {"id": str(task.id), "title": task.title, "status": task.status,
                 "column_id": str(task.column_id), "changes": changes}
    await publish_task_event(workspace_id, "task_updated", task_dict)

    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    column_id: uuid.UUID,
    task_id: uuid.UUID,
    membership: WorkspaceMember = Depends(require_member_or_above),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    workspace_id = get_workspace_id_for_column(column_id, db)

    db.delete(task)
    db.commit()

    await publish_task_event(workspace_id, "task_deleted", {"id": str(task_id)})


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    column_id: uuid.UUID,
    membership: WorkspaceMember = Depends(require_member_or_above),
    db: Session = Depends(get_db)
):
    return db.query(Task).filter(Task.column_id == column_id).order_by(Task.position).all()


@router.get("/{task_id}/activity", response_model=List[ActivityResponse])
def get_task_activity(
    column_id: uuid.UUID,
    task_id: uuid.UUID,
    membership: WorkspaceMember = Depends(require_member_or_above),
    db: Session = Depends(get_db)
):
    """Full activity history for a task — who did what and when."""
    return db.query(ActivityLog).filter(
        ActivityLog.task_id == task_id
    ).order_by(ActivityLog.created_at.desc()).all()
