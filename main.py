from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.base import Base, engine
from app.api.endpoints import auth, workspaces, tasks, websocket
from app.models import user, workspace, task


@asynccontextmanager
async def lifespan(app: FastAPI):
   _all(bind=engine)
    print("Database tables created")
    yield
    print("Shutting down")


app = FastAPI(
    title="Real-Time Collaborative Task Manager",
    description="A Trello-like backend with WebSocket real-time updates",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)
app.include_router(websocket.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "task-manager-api"}
