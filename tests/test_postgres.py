"""
PostgreSQL integration tests.

Unlike tests/test_*.py (which run against disposable SQLite for speed),
these tests run against a REAL PostgreSQL instance and verify things SQLite
can't: native ENUM types, unique/foreign-key constraint enforcement at the
database level, and NUMERIC precision.

How to run:
    1. Start Postgres (either via `docker compose up db` or a local install).
    2. Optionally set TEST_DATABASE_URL if it's not on localhost:5432 with
       the default docker-compose credentials.
    3. Run:  pytest tests/test_postgres.py -v

If Postgres isn't reachable, every test in this file is skipped (not
failed) with a clear reason, so this file is safe to leave in the suite
even when you're only running the fast SQLite tests.
"""
import os
import sys
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://medfind:medfind@localhost:5432/medfind",
)

EXPECTED_TABLES = {
    "users",
    "medicine_categories",
    "medicines",
    "medicine_aliases",
    "pharmacies",
    "pharmacy_products",
    "pharmacy_updates",
    "search_history",
}


def _postgres_available() -> bool:
    try:
        engine = create_engine(TEST_DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "PostgreSQL is not reachable at "
        f"{TEST_DATABASE_URL}. Start it with `docker compose up db` "
        "(or a local Postgres install) before running this file."
    ),
)


# ---------- Fixtures: real Postgres engine/session + a clean schema ----------

@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def pg_schema(pg_engine):
    """Create all app tables once for this module, drop them afterward."""
    from app.database import Base
    import app.models  # noqa: F401  (registers all model classes on Base)

    Base.metadata.drop_all(bind=pg_engine)
    Base.metadata.create_all(bind=pg_engine)
    yield
    Base.metadata.drop_all(bind=pg_engine)


@pytest.fixture
def pg_session(pg_engine, pg_schema):
    Session = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def api_client(pg_engine, pg_schema):
    """A FastAPI TestClient wired to the real Postgres instance instead of
    the SQLite database the main test suite uses."""
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    from fastapi.testclient import TestClient
    from app.database import get_db
    from app.main import app

    Session = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _unique_email(prefix="user"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


# ---------- Schema tests ----------

def test_connects_to_postgres(pg_engine):
    with pg_engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
    assert "PostgreSQL" in version


def test_all_expected_tables_exist(pg_engine, pg_schema):
    inspector = inspect(pg_engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {missing}"


def test_user_role_enum_type_exists(pg_engine, pg_schema):
    with pg_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT enumlabel FROM pg_enum "
            "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
            "WHERE pg_type.typname = 'user_role' ORDER BY enumlabel"
        )).fetchall()
    labels = {row[0] for row in result}
    assert labels == {"customer", "pharmacy_owner", "admin"}


def test_availability_status_enum_type_exists(pg_engine, pg_schema):
    with pg_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT enumlabel FROM pg_enum "
            "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
            "WHERE pg_type.typname = 'availability_status' ORDER BY enumlabel"
        )).fetchall()
    labels = {row[0] for row in result}
    assert labels == {"available", "limited_stock", "out_of_stock", "unknown"}


def test_foreign_key_constraints_exist(pg_engine, pg_schema):
    inspector = inspect(pg_engine)
    fks = inspector.get_foreign_keys("pharmacy_products")
    referenced_tables = {fk["referred_table"] for fk in fks}
    assert referenced_tables == {"pharmacies", "medicines"}


def test_unique_constraint_on_pharmacy_medicine_pair(pg_engine, pg_schema):
    inspector = inspect(pg_engine)
    unique_constraints = inspector.get_unique_constraints("pharmacy_products")
    columns_sets = [set(uc["column_names"]) for uc in unique_constraints]
    assert {"pharmacy_id", "medicine_id"} in columns_sets


# ---------- Constraint enforcement tests (writing real rows) ----------

def test_invalid_enum_value_rejected_by_postgres(pg_session):
    with pytest.raises((DataError, Exception)):
        pg_session.execute(text(
            "INSERT INTO users (full_name, email, password_hash, role) "
            "VALUES ('X', :email, 'hash', 'not_a_real_role')"
        ), {"email": _unique_email("badenum")})
        pg_session.commit()
    pg_session.rollback()


def test_duplicate_email_rejected_by_unique_index(pg_session):
    from app.models import User

    email = _unique_email("dupe")
    pg_session.add(User(full_name="A", email=email, password_hash="x", role="customer"))
    pg_session.commit()

    pg_session.add(User(full_name="B", email=email, password_hash="y", role="customer"))
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()


def test_duplicate_pharmacy_medicine_listing_rejected(pg_session):
    from app.models import User, Medicine, Pharmacy, PharmacyProduct

    owner = User(full_name="Owner", email=_unique_email("owner"),
                 password_hash="x", role="pharmacy_owner")
    pg_session.add(owner)
    pg_session.flush()

    medicine = Medicine(name="Test Medicine " + uuid.uuid4().hex[:6])
    pharmacy = Pharmacy(owner_user_id=owner.user_id, name="Test Pharmacy", address="1 St")
    pg_session.add_all([medicine, pharmacy])
    pg_session.flush()

    pg_session.add(PharmacyProduct(
        pharmacy_id=pharmacy.pharmacy_id, medicine_id=medicine.medicine_id, price=1.0
    ))
    pg_session.commit()

    # Same pharmacy + same medicine again should violate the unique constraint.
    pg_session.add(PharmacyProduct(
        pharmacy_id=pharmacy.pharmacy_id, medicine_id=medicine.medicine_id, price=2.0
    ))
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()


def test_foreign_key_violation_rejected(pg_session):
    from app.models import PharmacyProduct

    pg_session.add(PharmacyProduct(pharmacy_id=999999, medicine_id=999999, price=1.0))
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()


def test_numeric_price_precision_is_preserved(pg_session):
    from app.models import User, Medicine, Pharmacy, PharmacyProduct
    from decimal import Decimal

    owner = User(full_name="Owner", email=_unique_email("owner2"),
                 password_hash="x", role="pharmacy_owner")
    pg_session.add(owner)
    pg_session.flush()

    medicine = Medicine(name="Precision Med " + uuid.uuid4().hex[:6])
    pharmacy = Pharmacy(owner_user_id=owner.user_id, name="Precision Pharmacy", address="1 St")
    pg_session.add_all([medicine, pharmacy])
    pg_session.flush()

    product = PharmacyProduct(
        pharmacy_id=pharmacy.pharmacy_id, medicine_id=medicine.medicine_id,
        price=Decimal("19.99"),
    )
    pg_session.add(product)
    pg_session.commit()
    pg_session.refresh(product)

    assert product.price == Decimal("19.99")


# ---------- Full API flow against real Postgres ----------

def test_full_flow_end_to_end_against_real_postgres(api_client):
    """Mirrors the SQLite-based suite's coverage, but proves the same flow
    works against a real Postgres backend: register -> login -> admin
    creates a medicine + alias -> owner creates + gets pharmacy approved ->
    owner lists a product -> updates it (audit trail) -> search finds it
    by alias and sorts by distance."""
    email = _unique_email("alice")

    r = api_client.post("/api/users/", json={
        "full_name": "Alice Owner", "email": email,
        "password": "supersecret1", "role": "pharmacy_owner",
    })
    assert r.status_code == 201

    def login():
        r = api_client.post("/api/auth/login", data={"username": email, "password": "supersecret1"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    from app.database import get_db
    from app.main import app
    from app.models import User

    # Promote to admin directly (mirrors how a real deployment bootstraps its first admin).
    override = app.dependency_overrides[get_db]
    db = next(override())
    db.query(User).filter(User.email == email).update({"role": "admin"})
    db.commit()
    db.close()

    admin_headers = login()

    r = api_client.post("/api/medicines/", json={
        "name": "Paracetamol 500mg", "generic_name": "Paracetamol", "brand_name": "Panadol",
    }, headers=admin_headers)
    assert r.status_code == 201
    medicine_id = r.json()["medicine_id"]

    r = api_client.post(f"/api/medicines/{medicine_id}/aliases", json={
        "alias_name": "Panadol Extra", "alias_type": "brand",
    }, headers=admin_headers)
    assert r.status_code == 201

    db = next(override())
    db.query(User).filter(User.email == email).update({"role": "pharmacy_owner"})
    db.commit()
    db.close()
    owner_headers = login()

    r = api_client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St",
        "latitude": 50.1109, "longitude": 8.6821,
    }, headers=owner_headers)
    assert r.status_code == 201
    pharmacy_id = r.json()["pharmacy_id"]

    db = next(override())
    db.query(User).filter(User.email == email).update({"role": "admin"})
    db.commit()
    db.close()
    admin_headers = login()
    r = api_client.patch(f"/api/pharmacies/{pharmacy_id}/approve", headers=admin_headers)
    assert r.status_code == 200

    db = next(override())
    db.query(User).filter(User.email == email).update({"role": "pharmacy_owner"})
    db.commit()
    db.close()
    owner_headers = login()

    r = api_client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 5.99,
        "availability_status": "available", "stock_quantity": 50,
    }, headers=owner_headers)
    assert r.status_code == 201
    product_id = r.json()["product_id"]

    r = api_client.patch(f"/api/pharmacies/products/{product_id}", json={
        "price": 4.99, "stock_quantity": 40,
    }, headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["price"] == "4.99"

    # Audit trail check.
    from app.models import PharmacyUpdate
    db = next(override())
    updates = db.query(PharmacyUpdate).filter(PharmacyUpdate.product_id == product_id).all()
    db.close()
    assert len(updates) == 1
    assert float(updates[0].new_price) == 4.99

    # Alias-based search.
    r = api_client.get("/api/search/", params={"q": "Panadol Extra"})
    assert r.status_code == 200
    results = r.json()
    assert any(x["product_id"] == product_id for x in results)

    # Distance-sorted search.
    r = api_client.get("/api/search/", params={
        "q": "paracetamol", "latitude": 50.11, "longitude": 8.68, "sort": "distance",
    })
    assert r.status_code == 200
    assert r.json()[0]["distance_km"] is not None
