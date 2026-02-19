# app/api/endpoints/websocket.py
#
# This is the most important file in the project from an interview perspective.
# It demonstrates: WebSocket protocol, Redis Pub/Sub, async programming,
# connection management, and real-time event broadcasting.
#
# HOW IT WORKS:
# 1. Client connects to ws://server/ws/{workspace_id}?token=<jwt>
# 2. Server validates JWT (can't use headers in browser WebSockets)
# 3. Server subscribes to Redis channel: workspace:{workspace_id}
# 4. When any task in this workspace changes (via REST API), 
#    a message is published to this Redis channel
# 5. The WebSocket handler receives it and forwards to the client
# 6. On disconnect, we clean up the subscription
#
# Multiple clients connected to the same workspace all get the same updates
# because they all subscribe to the same Redis channel.

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
    """
    Tracks active WebSocket connections per workspace.
    This lives in memory — fine for a single server.
    For multiple servers, you'd use Redis to coordinate.
    
    Structure: {workspace_id: [WebSocket, WebSocket, ...]}
    """
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
        """Send a message to ALL connected clients in a workspace."""
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


# Singleton — one manager for the entire app lifetime
manager = ConnectionManager()


@router.websocket("/ws/{workspace_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    workspace_id: uuid.UUID,
    token: str = Query(...),  # JWT passed as query param since WS can't use headers
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time workspace updates.
    
    Connect: ws://localhost:8000/ws/{workspace_id}?token=<access_token>
    
    The client receives JSON messages whenever a task is created, updated, or deleted.
    Message format: {"event": "task_updated", "data": {...}}
    """
    # --- Authentication ---
    # WebSocket clients can't set custom headers in browsers,
    # so we accept the JWT as a query parameter instead.
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        await websocket.close(code=4001, reason="User not found")
        return

    # --- Authorization ---
    # Check workspace membership before allowing connection
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()

    if not membership:
        await websocket.close(code=4003, reason="Not a workspace member")
        return

    # --- Connection Established ---
    workspace_id_str = str(workspace_id)
    await manager.connect(websocket, workspace_id_str)

    # Send a welcome message confirming connection
    await websocket.send_text(json.dumps({
        "event": "connected",
        "data": {
            "workspace_id": workspace_id_str,
            "user_id": str(user.id),
            "message": "Connected to workspace real-time updates"
        }
    }))

    # --- Redis Pub/Sub Subscription ---
    # Create a pubsub object and subscribe to this workspace's channel
    pubsub = async_redis.pubsub()
    await pubsub.subscribe(f"workspace:{workspace_id_str}")

    try:
        # Run two concurrent tasks:
        # 1. Listen for Redis messages and forward to WebSocket client
        # 2. Listen for WebSocket messages (ping/pong keepalive)
        await asyncio.gather(
            _redis_listener(pubsub, websocket, workspace_id_str),
            _websocket_listener(websocket)
        )
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Always clean up on disconnect
        manager.disconnect(websocket, workspace_id_str)
        await pubsub.unsubscribe(f"workspace:{workspace_id_str}")
        await pubsub.close()


async def _redis_listener(pubsub, websocket: WebSocket, workspace_id: str):
    """
    Listen for messages on the Redis Pub/Sub channel.
    When a task changes (published by tasks.py), forward it to the WebSocket client.
    
    pubsub.listen() is an async generator that yields messages as they arrive.
    message["type"] == "message" filters out subscription confirmations.
    """
    async for message in pubsub.listen():
        if message["type"] == "message":
            # Forward the Redis message directly to the WebSocket client
            await websocket.send_text(message["data"])


async def _websocket_listener(websocket: WebSocket):
    """
    Listen for messages FROM the client (keepalive pings).
    Without this, the connection might time out.
    Clients can send {"type": "ping"} to keep the connection alive.
    """
    while True:
        data = await websocket.receive_text()
        msg = json.loads(data)
        if msg.get("type") == "ping":
            await websocket.send_text(json.dumps({"type": "pong"}))
