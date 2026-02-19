# Real-Time Collaborative Task Manager — Project Structure

```
taskmanager/
│
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   └── endpoints/
│   │       ├── auth.py          # Login, register, refresh token
│   │       ├── users.py         # User profile endpoints
│   │       ├── workspaces.py    # Workspace CRUD + member management
│   │       ├── boards.py        # Board CRUD
│   │       ├── columns.py       # Column CRUD
│   │       ├── tasks.py         # Task CRUD + assignment
│   │       └── websocket.py     # WebSocket real-time endpoint
│   ├── core/
│   │   ├── config.py            # Environment variables / settings
│   │   ├── security.py          # JWT creation, hashing, verification
│   │   └── dependencies.py      # Reusable FastAPI dependencies
│   ├── db/
│   │   ├── base.py              # SQLAlchemy base + session
│   │   └── redis.py             # Redis connection
│   ├── models/                  # SQLAlchemy ORM models (DB tables)
│   │   ├── user.py
│   │   ├── workspace.py
│   │   ├── board.py
│   │   ├── task.py
│   │   └── activity.py
│   ├── schemas/                 # Pydantic schemas (request/response shapes)
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── workspace.py
│   │   ├── board.py
│   │   ├── task.py
│   │   └── activity.py
│   ├── services/                # Business logic layer
│   │   ├── auth_service.py
│   │   ├── workspace_service.py
│   │   ├── task_service.py
│   │   └── pubsub_service.py    # Redis Pub/Sub logic
│   └── worker/
│       ├── celery_app.py        # Celery app instance
│       └── tasks.py             # Background tasks (email notifications)
│
├── tests/
│   ├── conftest.py              # pytest fixtures
│   ├── test_auth.py
│   ├── test_tasks.py
│   └── test_websocket.py
│
├── alembic/                     # Database migrations
│   ├── env.py
│   └── versions/
│
├── .env                         # Environment variables (never commit this)
├── .env.example                 # Template for env vars
├── docker-compose.yml           # All 4 services: app, db, redis, celery
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── README.md
```
