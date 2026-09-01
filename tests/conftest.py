"""
Shared pytest fixtures.

Tests run against a fresh, disposable SQLite database instead of Postgres,
so the suite runs anywhere with no external services and never touches a
real database. This is done by setting DATABASE_URL *before* the app
package is imported, since app.database builds its engine at import time.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DATABASE_URL = "sqlite:///./test_medfind.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Re-use a dedicated engine/session for direct DB access in tests (asserting
# on audit-trail rows, promoting a user to admin, etc). Same URL as the app.
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Each test gets a clean rate-limit bucket, so one test's requests
    can't push a later, unrelated test over the 30/minute search limit."""
    from app.rate_limit import limiter
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def _fresh_database():
    """Recreate all tables before every test so tests don't leak state."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


# ---------- Convenience helpers used across test files ----------

def register_user(client, email="user@example.com", password="supersecret1",
                   role="customer", full_name="Test User"):
    return client.post("/api/users/", json={
        "full_name": full_name,
        "email": email,
        "password": password,
        "role": role,
    })


def login(client, email="user@example.com", password="supersecret1"):
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def promote_to_admin(email):
    """Directly flips a user's role in the test DB (mirrors how a real
    deployment would bootstrap its first admin)."""
    db = TestingSessionLocal()
    from app.models import User
    user = db.query(User).filter(User.email == email).first()
    user.role = "admin"
    db.commit()
    db.close()
