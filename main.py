# app/main.py
#
# The FastAPI application entry point.
# Registers all routers and sets up startup/shutdown events.
# This is what uvicorn runs: uvicorn app.main:app --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.base import Base, engine
from app.api.endpoints import auth, workspaces, tasks, websocket

# Import all models so SQLAlchemy knows about them when creating tables
from app.models import user, workspace, task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Creates all DB tables on startup (for dev — use Alembic migrations in production).
    """
    # Startup
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    yield
    # Shutdown (cleanup if needed)
    print("Shutting down")


app = FastAPI(
    title="Real-Time Collaborative Task Manager",
    description="A Trello-like backend with WebSocket real-time updates",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — allows your frontend (e.g., React on port 3000) to call this API
# In production, replace "*" with your actual frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)
app.include_router(websocket.router)


@app.get("/health")
def health_check():
    """Simple health check endpoint. Used by Docker and load balancers."""
    return {"status": "healthy", "service": "task-manager-api"}
