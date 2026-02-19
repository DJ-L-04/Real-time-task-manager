# tests/test_auth.py

def test_register_success(client):
    response = client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "password123",
        "full_name": "New User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert "hashed_password" not in data  # never expose this


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "pass123"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client):
    client.post("/auth/register", json={"email": "user@example.com", "password": "pass123"})
    response = client.post("/auth/login", json={"email": "user@example.com", "password": "pass123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "user@example.com", "password": "correct"})
    response = client.post("/auth/login", json={"email": "user@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_logout(client, auth_headers):
    response = client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 200


def test_protected_endpoint_without_token(client):
    response = client.get("/workspaces/")
    assert response.status_code == 403  # no token = forbidden


# tests/test_workspaces.py

def test_create_workspace(client, auth_headers):
    response = client.post("/workspaces/", json={
        "name": "My Workspace",
        "description": "Test workspace"
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Workspace"
    assert "id" in data


def test_list_workspaces(client, auth_headers):
    client.post("/workspaces/", json={"name": "WS 1"}, headers=auth_headers)
    client.post("/workspaces/", json={"name": "WS 2"}, headers=auth_headers)
    response = client.get("/workspaces/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_non_member_cannot_access_workspace(client, auth_headers):
    # Create workspace with user 1
    ws = client.post("/workspaces/", json={"name": "Private WS"}, headers=auth_headers).json()

    # Register user 2
    client.post("/auth/register", json={"email": "other@example.com", "password": "pass"})
    login = client.post("/auth/login", json={"email": "other@example.com", "password": "pass"}).json()
    other_headers = {"Authorization": f"Bearer {login['access_token']}"}

    # User 2 tries to access workspace — should be forbidden
    response = client.get(f"/workspaces/{ws['id']}", headers=other_headers)
    assert response.status_code == 403
