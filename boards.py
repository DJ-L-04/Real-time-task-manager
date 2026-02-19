# app/api/endpoints/boards.py
#
# Board and Column CRUD.
# Boards live inside workspaces. Columns live inside boards.
# RBAC enforced via workspace membership check.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.db.base import get_db
from app.models.workspace import Board, BoardColumn, WorkspaceMember
from app.core.dependencies import get_current_user, require_member_or_above, require_admin
from app.schemas.schemas import BoardCreate, BoardResponse, ColumnCreate, ColumnResponse
from app.models.user import User

router = APIRouter(prefix="/workspaces/{workspace_id}/boards", tags=["Boards"])
column_router = APIRouter(prefix="/boards/{board_id}/columns", tags=["Columns"])


@router.post("/", response_model=BoardResponse, status_code=201)
def create_board(
    workspace_id: uuid.UUID,
    payload: BoardCreate,
    membership: WorkspaceMember = Depends(require_member_or_above),
    db: Session = Depends(get_db)
):
    board = Board(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


@router.get("/", response_model=List[BoardResponse])
def list_boards(
    workspace_id: uuid.UUID,
    membership: WorkspaceMember = Depends(require_member_or_above),
    db: Session = Depends(get_db)
):
    return db.query(Board).filter(Board.workspace_id == workspace_id).all()


@router.delete("/{board_id}", status_code=204)
def delete_board(
    workspace_id: uuid.UUID,
    board_id: uuid.UUID,
    membership: WorkspaceMember = Depends(require_admin),  # only admin can delete
    db: Session = Depends(get_db)
):
    board = db.query(Board).filter(Board.id == board_id, Board.workspace_id == workspace_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    db.delete(board)
    db.commit()


# Column endpoints
@column_router.post("/", response_model=ColumnResponse, status_code=201)
def create_column(
    board_id: uuid.UUID,
    payload: ColumnCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    column = BoardColumn(
        board_id=board_id,
        name=payload.name,
        position=payload.position
    )
    db.add(column)
    db.commit()
    db.refresh(column)
    return column


@column_router.get("/", response_model=List[ColumnResponse])
def list_columns(
    board_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(BoardColumn).filter(
        BoardColumn.board_id == board_id
    ).order_by(BoardColumn.position).all()
