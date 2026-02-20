import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.redis import async_redis
from app.core.security import decode_token
from app.models.user import User
from app.models.workspace import WorkspaceMember

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, workspace_id: str):
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)

    def disconnect(self, websocket: WebSocket, workspace_id: str):
        if workspace_id in self.active_connections:
            self.active_connections[workspace_id].remove(websocket)
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]

    async def broadcast_to_workspace(self, workspace_id: str, message: str):
        connections = self.active_connections.get(workspace_id, [])
        dead_connections = []
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)
        # Clean up dead connections
        for dead in dead_connections:
            connections.remove(dead)

manager = ConnectionManager()

@router.websocket("/ws/{workspace_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    workspace_id: uuid.UUID,
    token: str = Query(...), 
    db: Session = Depends(get_db)
):
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        await websocket.close(code=4001, reason="User not found")
        return

    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()

    if not membership:
        await websocket.close(code=4003, reason="Not a workspace member")
        return

    workspace_id_str = str(workspace_id)
    await manager.connect(websocket, workspace_id_str)

    await websocket.send_text(json.dumps({
        "event": "connected",
        "data": {
            "workspace_id": workspace_id_str,
            "user_id": str(user.id),
            "message": "Connected to workspace real-time updates"
        }
    }))

    pubsub = async_redis.pubsub()
    await pubsub.subscribe(f"workspace:{workspace_id_str}")

    try:
        await asyncio.gather(
            _redis_listener(pubsub, websocket, workspace_id_str),
            _websocket_listener(websocket)
        )
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, workspace_id_str)
        await pubsub.unsubscribe(f"workspace:{workspace_id_str}")
        await pubsub.close()


async def _redis_listener(pubsub, websocket: WebSocket, workspace_id: str):
    async for message in pubsub.listen():
        if message["type"] == "message":
            await websocket.send_text(message["data"])


async def _websocket_listener(websocket: WebSocket):
    while True:
        data = await websocket.receive_text()
        msg = json.loads(data)
        if msg.get("type") == "ping":
            await websocket.send_text(json.dumps({"type": "pong"}))
