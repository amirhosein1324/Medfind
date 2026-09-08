from .conftest import register_user, login, auth_headers


def test_register_user_success(client):
    r = register_user(client, email="alice@example.com", role="customer")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "customer"
    assert body["is_active"] is True
    # password must never be echoed back
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_rejected(client):
    register_user(client, email="dup@example.com")
    r = register_user(client, email="dup@example.com")
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"].lower()


def test_register_rejects_admin_role_self_service(client):
    r = register_user(client, email="wannabe-admin@example.com", role="admin")
    assert r.status_code == 400


def test_register_rejects_short_password(client):
    r = client.post("/api/users/", json={
        "full_name": "Short Pw",
        "email": "shortpw@example.com",
        "password": "short",
        "role": "customer",
    })
    assert r.status_code == 422


def test_login_success_returns_token(client):
    register_user(client, email="bob@example.com", password="supersecret1")
    r = client.post("/api/auth/login", data={
        "username": "bob@example.com", "password": "supersecret1"
    })
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 10


def test_login_wrong_password_rejected(client):
    register_user(client, email="carol@example.com", password="supersecret1")
    r = client.post("/api/auth/login", data={
        "username": "carol@example.com", "password": "wrongpassword"
    })
    assert r.status_code == 401


def test_login_unknown_email_rejected(client):
    r = client.post("/api/auth/login", data={
        "username": "nobody@example.com", "password": "whatever123"
    })
    assert r.status_code == 401


def test_get_my_profile_requires_auth(client):
    r = client.get("/api/users/me")
    assert r.status_code == 401


def test_get_my_profile_returns_current_user(client):
    register_user(client, email="dave@example.com")
    token = login(client, email="dave@example.com")
    r = client.get("/api/users/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == "dave@example.com"


def test_user_cannot_view_another_users_profile(client):
    register_user(client, email="eve@example.com")
    register_user(client, email="frank@example.com")
    eve_token = login(client, email="eve@example.com")

    frank_id = client.get(
        "/api/users/me",
        headers=auth_headers(login(client, email="frank@example.com")),
    ).json()["user_id"]

    r = client.get(f"/api/users/{frank_id}", headers=auth_headers(eve_token))
    assert r.status_code == 403


def test_list_users_requires_admin(client):
    register_user(client, email="regular@example.com")
    token = login(client, email="regular@example.com")
    r = client.get("/api/users/", headers=auth_headers(token))
    assert r.status_code == 403


def test_malformed_token_rejected(client):
    r = client.get(
        "/api/users/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert r.status_code == 401


def test_deactivated_user_token_rejected(client):
    register_user(client, email="ghost@example.com", password="supersecret1")
    token = login(client, email="ghost@example.com")

    from .conftest import TestingSessionLocal
    from app.models import User
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "ghost@example.com").first()
    user.is_active = False
    db.commit()
    db.close()

    r = client.get("/api/users/me", headers=auth_headers(token))
    assert r.status_code == 401
