# Real-Time Collaborative Task Manager

A production-grade backend built with FastAPI, PostgreSQL, Redis (Pub/Sub + Celery broker), and WebSockets. 
Supports real-time collaboration, role-based access control, and async background jobs.

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

`PROJECT_STRUCTURE.md` for full breakdown.
