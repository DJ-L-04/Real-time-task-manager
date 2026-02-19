# Real-Time Collaborative Task Manager

A production-grade backend built with FastAPI, PostgreSQL, Redis (Pub/Sub + Celery broker), and WebSockets. 
Supports real-time collaboration, role-based access control, and async background jobs.

## Architecture

```
Client (REST)     →  FastAPI  →  PostgreSQL (persistence)
Client (WebSocket) →  FastAPI  →  Redis Pub/Sub → broadcast to all workspace clients
Task change event  →  Celery  →  Redis broker → email notification worker
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy ORM |
| Real-time | WebSockets + Redis Pub/Sub |
| Background Jobs | Celery + Redis |
| Auth | JWT (access + refresh tokens) |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |

## Features

- **Real-time updates** — WebSocket endpoint broadcasts task changes to all connected workspace members instantly
- **Redis Pub/Sub** — decouples REST operations from WebSocket delivery
- **RBAC** — Admin / Member / Viewer roles enforced at the dependency level
- **JWT auth** — Access + refresh token rotation, logout invalidation
- **Celery workers** — Email notifications are async, never blocking API responses
- **Activity log** — Immutable audit trail for every task action
- **Docker Compose** — One command to run all 4 services

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd taskmanager
cp .env.example .env  # fill in your values

# Run everything with Docker
docker-compose up --build

# API available at: http://localhost:8000
# Docs available at: http://localhost:8000/docs
```

## Running Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (or use Docker for just these)
docker-compose up db redis -d

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app.worker.celery_app.celery_app worker --loglevel=info
```

## Running Tests

```bash
pytest tests/ -v
```

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Create account |
| POST | /auth/login | Get token pair |
| POST | /auth/refresh | Rotate tokens |
| POST | /auth/logout | Invalidate refresh token |

### Workspaces
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /workspaces/ | Create workspace |
| GET | /workspaces/ | List my workspaces |
| GET | /workspaces/{id} | Get workspace |
| POST | /workspaces/{id}/members | Add member (Admin only) |
| DELETE | /workspaces/{id}/members/{uid} | Remove member (Admin only) |

### Boards & Columns
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /workspaces/{id}/boards/ | Create board |
| GET | /workspaces/{id}/boards/ | List boards |
| POST | /boards/{id}/columns/ | Create column |
| GET | /boards/{id}/columns/ | List columns |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /columns/{id}/tasks/ | Create task |
| GET | /columns/{id}/tasks/ | List tasks |
| PATCH | /columns/{id}/tasks/{task_id} | Update task |
| DELETE | /columns/{id}/tasks/{task_id} | Delete task |
| GET | /columns/{id}/tasks/{task_id}/activity | Task history |

### WebSocket
```
ws://localhost:8000/ws/{workspace_id}?token=<access_token>
```

**Messages received:**
```json
{"event": "task_created", "data": {"id": "...", "title": "..."}}
{"event": "task_updated", "data": {"id": "...", "changes": {...}}}
{"event": "task_deleted", "data": {"id": "..."}}
```

**Keepalive:**
```json
// Send: {"type": "ping"}
// Receive: {"type": "pong"}
```

## Project Structure

See `PROJECT_STRUCTURE.md` for full breakdown.

## Key Design Decisions

**Why Redis Pub/Sub over polling?** Polling requires clients to hit the DB every N seconds. 
Pub/Sub pushes updates only when changes occur — significantly lower server load and near-zero latency.

**Why Celery for emails?** Email sending can take 1-3 seconds. Blocking the API response 
would hurt user experience. Celery offloads it to a background worker with retry logic.

**Why refresh token rotation?** Storing refresh tokens in DB allows logout invalidation. 
Rotation means a stolen refresh token can only be used once before the legitimate user's 
next login invalidates it.

**Why UUIDs over integer IDs?** Prevents enumeration attacks — you can't guess resource IDs 
by incrementing integers.
