from .conftest import register_user, login, auth_headers, promote_to_admin


def _make_admin(client, email="admin@example.com"):
    register_user(client, email=email, role="pharmacy_owner")
    promote_to_admin(email)
    return auth_headers(login(client, email=email))


def _make_pharmacy_owner(client, email="owner@example.com"):
    register_user(client, email=email, role="pharmacy_owner")
    return auth_headers(login(client, email=email))


def _make_medicine(client, admin_headers, name="Paracetamol 500mg"):
    return client.post("/api/medicines/", json={"name": name}, headers=admin_headers).json()["medicine_id"]


def test_create_pharmacy_requires_pharmacy_owner_or_admin(client):
    register_user(client, email="cust@example.com", role="customer")
    token = login(client, email="cust@example.com")
    r = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=auth_headers(token))
    assert r.status_code == 403


def test_create_pharmacy_starts_unapproved(client):
    owner_headers = _make_pharmacy_owner(client)
    r = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St",
        "latitude": 50.11, "longitude": 8.68,
    }, headers=owner_headers)
    assert r.status_code == 201
    assert r.json()["is_approved"] is False


def test_unapproved_pharmacy_not_publicly_listed(client):
    owner_headers = _make_pharmacy_owner(client)
    client.post("/api/pharmacies/", json={
        "name": "Hidden Pharmacy", "address": "1 Nowhere St"
    }, headers=owner_headers)

    r = client.get("/api/pharmacies/")
    assert r.status_code == 200
    assert r.json() == []


def test_admin_can_approve_pharmacy(client):
    owner_headers = _make_pharmacy_owner(client)
    admin_headers = _make_admin(client)

    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]

    r = client.patch(f"/api/pharmacies/{pharmacy_id}/approve", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_approved"] is True

    listed = client.get("/api/pharmacies/").json()
    assert any(p["pharmacy_id"] == pharmacy_id for p in listed)


def test_non_admin_cannot_approve_pharmacy(client):
    owner_headers = _make_pharmacy_owner(client)
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]

    r = client.patch(f"/api/pharmacies/{pharmacy_id}/approve", headers=owner_headers)
    assert r.status_code == 403


def test_list_my_pharmacies(client):
    owner_headers = _make_pharmacy_owner(client, email="owner1@example.com")
    other_headers = _make_pharmacy_owner(client, email="owner2@example.com")

    client.post("/api/pharmacies/", json={"name": "Mine", "address": "A St"}, headers=owner_headers)
    client.post("/api/pharmacies/", json={"name": "Not Mine", "address": "B St"}, headers=other_headers)

    r = client.get("/api/pharmacies/mine", headers=owner_headers)
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert names == ["Mine"]


def test_create_product_listing_as_owner(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = _make_medicine(client, admin_headers)
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]

    r = client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 5.99,
        "availability_status": "available", "stock_quantity": 50,
    }, headers=owner_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["price"] == "5.99"
    assert body["availability_status"] == "available"


def test_stranger_cannot_add_listing_to_someone_elses_pharmacy(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client, email="realowner@example.com")
    stranger_headers = _make_pharmacy_owner(client, email="stranger@example.com")

    medicine_id = _make_medicine(client, admin_headers)
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]

    r = client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 5.99,
    }, headers=stranger_headers)
    assert r.status_code == 403


def test_update_listing_writes_audit_trail(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = _make_medicine(client, admin_headers)
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]
    product_id = client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 5.99,
        "availability_status": "available", "stock_quantity": 50,
    }, headers=owner_headers).json()["product_id"]

    r = client.patch(f"/api/pharmacies/products/{product_id}", json={
        "price": 4.99, "stock_quantity": 40,
    }, headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["price"] == "4.99"
    assert body["stock_quantity"] == 40

    # Verify the audit row exists with correct before/after values.
    from .conftest import TestingSessionLocal
    from app.models import PharmacyUpdate

    db = TestingSessionLocal()
    updates = db.query(PharmacyUpdate).filter(PharmacyUpdate.product_id == product_id).all()
    db.close()

    assert len(updates) == 1
    assert float(updates[0].old_price) == 5.99
    assert float(updates[0].new_price) == 4.99
    assert updates[0].old_stock == 50
    assert updates[0].new_stock == 40


def test_stranger_cannot_update_someone_elses_listing(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client, email="realowner2@example.com")
    stranger_headers = _make_pharmacy_owner(client, email="stranger2@example.com")

    medicine_id = _make_medicine(client, admin_headers)
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]
    product_id = client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 5.99,
    }, headers=owner_headers).json()["product_id"]

    r = client.patch(f"/api/pharmacies/products/{product_id}", json={
        "price": 0.01,
    }, headers=stranger_headers)
    assert r.status_code == 403


def test_admin_can_update_any_listing(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)

    medicine_id = _make_medicine(client, admin_headers)
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]
    product_id = client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 5.99,
    }, headers=owner_headers).json()["product_id"]

    r = client.patch(f"/api/pharmacies/products/{product_id}", json={
        "availability_status": "out_of_stock",
    }, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["availability_status"] == "out_of_stock"


def test_update_nonexistent_listing_404s(client):
    owner_headers = _make_pharmacy_owner(client)
    r = client.patch("/api/pharmacies/products/9999", json={"price": 1.0}, headers=owner_headers)
    assert r.status_code == 404
