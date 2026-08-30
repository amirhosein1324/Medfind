from .conftest import register_user, login, auth_headers, promote_to_admin


def _admin_headers(client, email="admin@example.com"):
    register_user(client, email=email, role="pharmacy_owner")
    promote_to_admin(email)
    return auth_headers(login(client, email=email))


def test_create_medicine_requires_admin(client):
    register_user(client, email="cust@example.com", role="customer")
    token = login(client, email="cust@example.com")
    r = client.post("/api/medicines/", json={"name": "Ibuprofen"}, headers=auth_headers(token))
    assert r.status_code == 403


def test_create_medicine_as_admin(client):
    headers = _admin_headers(client)
    r = client.post("/api/medicines/", json={
        "name": "Paracetamol 500mg",
        "generic_name": "Paracetamol",
        "brand_name": "Panadol",
        "dosage": "500mg",
        "form": "Tablet",
    }, headers=headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Paracetamol 500mg"
    assert "medicine_id" in body


def test_list_medicines_is_public(client):
    headers = _admin_headers(client)
    client.post("/api/medicines/", json={"name": "Aspirin"}, headers=headers)

    r = client.get("/api/medicines/")
    assert r.status_code == 200
    assert any(m["name"] == "Aspirin" for m in r.json())


def test_search_medicines_by_partial_name(client):
    headers = _admin_headers(client)
    client.post("/api/medicines/", json={"name": "Amoxicillin 250mg"}, headers=headers)
    client.post("/api/medicines/", json={"name": "Paracetamol 500mg"}, headers=headers)

    r = client.get("/api/medicines/", params={"q": "amox"})
    assert r.status_code == 200
    names = [m["name"] for m in r.json()]
    assert names == ["Amoxicillin 250mg"]


def test_get_medicine_not_found(client):
    r = client.get("/api/medicines/9999")
    assert r.status_code == 404


def test_add_alias_requires_admin(client):
    admin_headers = _admin_headers(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Paracetamol"}, headers=admin_headers
    ).json()["medicine_id"]

    register_user(client, email="notadmin@example.com", role="pharmacy_owner")
    token = login(client, email="notadmin@example.com")

    r = client.post(
        f"/api/medicines/{medicine_id}/aliases",
        json={"alias_name": "Panadol"},
        headers=auth_headers(token),
    )
    assert r.status_code == 403


def test_add_and_list_alias(client):
    admin_headers = _admin_headers(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Paracetamol"}, headers=admin_headers
    ).json()["medicine_id"]

    r = client.post(
        f"/api/medicines/{medicine_id}/aliases",
        json={"alias_name": "Panadol Extra", "alias_type": "brand"},
        headers=admin_headers,
    )
    assert r.status_code == 201

    r = client.get(f"/api/medicines/{medicine_id}/aliases")
    assert r.status_code == 200
    assert r.json()[0]["alias_name"] == "Panadol Extra"


def test_add_alias_to_missing_medicine_404s(client):
    admin_headers = _admin_headers(client)
    r = client.post(
        "/api/medicines/9999/aliases",
        json={"alias_name": "Ghost"},
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_create_and_list_categories(client):
    admin_headers = _admin_headers(client)
    r = client.post(
        "/api/medicines/categories",
        json={"name": "Pain Relief", "description": "Analgesics"},
        headers=admin_headers,
    )
    assert r.status_code == 201

    r = client.get("/api/medicines/categories")
    assert r.status_code == 200
    assert any(c["name"] == "Pain Relief" for c in r.json())


def test_duplicate_category_rejected(client):
    admin_headers = _admin_headers(client)
    client.post("/api/medicines/categories", json={"name": "Antibiotics"}, headers=admin_headers)
    r = client.post("/api/medicines/categories", json={"name": "Antibiotics"}, headers=admin_headers)
    assert r.status_code == 400
