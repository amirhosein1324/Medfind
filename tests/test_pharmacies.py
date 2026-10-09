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


# ---------- Added for the frontend: names in listings + admin queue ----------

def test_listing_response_includes_medicine_name(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post("/api/medicines/", json={
        "name": "Paracetamol 500mg", "dosage": "500mg", "form": "Tablet",
    }, headers=admin_headers).json()["medicine_id"]
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "City Pharmacy", "address": "123 Main St"
    }, headers=owner_headers).json()["pharmacy_id"]
    client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 5.99,
    }, headers=owner_headers)

    listed = client.get(f"/api/pharmacies/{pharmacy_id}/products").json()
    assert listed[0]["medicine_name"] == "Paracetamol 500mg"
    assert listed[0]["medicine_detail"] == "500mg Tablet"


def test_admin_all_requires_admin(client):
    owner_headers = _make_pharmacy_owner(client)
    assert client.get("/api/pharmacies/admin/all", headers=owner_headers).status_code == 403


def test_admin_queue_lists_pending_with_owner_and_revoke_works(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client, email="o2@example.com")
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "Queue Pharmacy", "address": "1 Queue St"
    }, headers=owner_headers).json()["pharmacy_id"]

    pending = client.get("/api/pharmacies/admin/all", params={"status": "pending"}, headers=admin_headers).json()
    assert [p["name"] for p in pending] == ["Queue Pharmacy"]
    assert pending[0]["owner_email"] == "o2@example.com"

    client.patch(f"/api/pharmacies/{pharmacy_id}/approve", headers=admin_headers)
    assert client.get("/api/pharmacies/admin/all", params={"status": "pending"}, headers=admin_headers).json() == []

    r = client.patch(f"/api/pharmacies/{pharmacy_id}/revoke", headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_approved"] is False
    assert client.get("/api/pharmacies/").json() == []


def _listing_setup(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client, email="conf-owner@example.com")
    medicine_id = _make_medicine(client, admin_headers, name="Confirm Med")
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "Confirm Pharmacy", "address": "1 Confirm St"
    }, headers=owner_headers).json()["pharmacy_id"]
    product_id = client.post(f"/api/pharmacies/{pharmacy_id}/products", json={
        "medicine_id": medicine_id, "price": 2.5, "availability_status": "available",
    }, headers=owner_headers).json()["product_id"]
    return owner_headers, pharmacy_id, product_id


def _set_last_updated_to_old(product_id):
    from datetime import datetime, timedelta
    from .conftest import TestingSessionLocal
    from app.models import PharmacyProduct
    db = TestingSessionLocal()
    p = db.query(PharmacyProduct).filter(PharmacyProduct.product_id == product_id).first()
    p.last_updated = datetime.utcnow() - timedelta(days=5)
    db.commit()
    db.close()


def test_confirm_product_refreshes_timestamp_and_logs(client):
    from datetime import datetime
    owner_headers, pharmacy_id, product_id = _listing_setup(client)
    _set_last_updated_to_old(product_id)

    r = client.post(f"/api/pharmacies/products/{product_id}/confirm", headers=owner_headers)
    assert r.status_code == 200
    updated = datetime.fromisoformat(r.json()["last_updated"])
    assert (datetime.utcnow() - updated).total_seconds() < 60
    assert r.json()["price"] == "2.50"  # values untouched

    history = client.get(f"/api/pharmacies/{pharmacy_id}/updates", headers=owner_headers).json()
    assert len(history) == 1
    assert history[0]["old_price"] == history[0]["new_price"]


def test_confirm_all_refreshes_every_listing(client):
    from datetime import datetime
    owner_headers, pharmacy_id, product_id = _listing_setup(client)
    _set_last_updated_to_old(product_id)

    r = client.post(f"/api/pharmacies/{pharmacy_id}/confirm-all", headers=owner_headers)
    assert r.status_code == 200 and r.json()["confirmed"] == 1

    listed = client.get(f"/api/pharmacies/{pharmacy_id}/products").json()
    updated = datetime.fromisoformat(listed[0]["last_updated"])
    assert (datetime.utcnow() - updated).total_seconds() < 60


def test_stranger_cannot_confirm_someone_elses_listing(client):
    _, _, product_id = _listing_setup(client)
    stranger_headers = _make_pharmacy_owner(client, email="stranger-conf@example.com")
    r = client.post(f"/api/pharmacies/products/{product_id}/confirm", headers=stranger_headers)
    assert r.status_code == 403
