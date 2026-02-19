# tests/conftest.py
#
# pytest fixtures — setup code shared across all test files.
# The test_db fixture creates a fresh in-memory SQLite DB for each test.
# The client fixture gives us a TestClient that uses the test DB.
# This means tests never touch your real PostgreSQL database.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base, get_db

# Use SQLite in-memory for tests — fast, no setup required
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """Create fresh tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """TestClient with DB dependency overridden to use test SQLite DB."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Helper fixture: register + login a user, return tokens."""
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    })
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })
    return response.json()


@pytest.fixture
def auth_headers(registered_user):
    """Auth headers for authenticated requests."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
