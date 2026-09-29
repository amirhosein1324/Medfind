from .conftest import register_user, login, auth_headers, promote_to_admin


def _make_admin(client, email="admin@example.com"):
    register_user(client, email=email, role="pharmacy_owner")
    promote_to_admin(email)
    return auth_headers(login(client, email=email))


def _make_pharmacy_owner(client, email="owner@example.com"):
    register_user(client, email=email, role="pharmacy_owner")
    return auth_headers(login(client, email=email))


def _approved_pharmacy(client, admin_headers, owner_headers, name, lat=None, lon=None):
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": name, "address": f"{name} St", "latitude": lat, "longitude": lon,
    }, headers=owner_headers).json()["pharmacy_id"]
    client.patch(f"/api/pharmacies/{pharmacy_id}/approve", headers=admin_headers)
    return pharmacy_id


def _listing(client, owner_headers, pharmacy_id, medicine_id, **kwargs):
    payload = {"medicine_id": medicine_id, **kwargs}
    return client.post(
        f"/api/pharmacies/{pharmacy_id}/products", json=payload, headers=owner_headers
    ).json()


def test_search_requires_query_param(client):
    r = client.get("/api/search/")
    assert r.status_code == 422


def test_search_returns_empty_for_no_matches(client):
    r = client.get("/api/search/", params={"q": "nonexistent-drug-xyz"})
    assert r.status_code == 200
<<<<<<< HEAD
    assert r.json() == []
=======
    assert r.json()["results"] == []
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa


def test_search_matches_by_generic_and_brand_name(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post("/api/medicines/", json={
        "name": "Paracetamol 500mg", "generic_name": "Paracetamol", "brand_name": "Panadol"
    }, headers=admin_headers).json()["medicine_id"]
    pharmacy_id = _approved_pharmacy(client, admin_headers, owner_headers, "City Pharmacy")
    _listing(client, owner_headers, pharmacy_id, medicine_id, price=5.99, availability_status="available")

    for q in ["paracetamol", "panadol", "500mg"]:
        r = client.get("/api/search/", params={"q": q})
        assert r.status_code == 200, q
<<<<<<< HEAD
        assert len(r.json()) == 1, f"query '{q}' should match"
=======
        assert len(r.json()["results"]) == 1, f"query '{q}' should match"
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa


def test_search_matches_by_alias(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Paracetamol 500mg"}, headers=admin_headers
    ).json()["medicine_id"]
    client.post(f"/api/medicines/{medicine_id}/aliases", json={
        "alias_name": "Panadol Extra", "alias_type": "brand"
    }, headers=admin_headers)

    pharmacy_id = _approved_pharmacy(client, admin_headers, owner_headers, "City Pharmacy")
    _listing(client, owner_headers, pharmacy_id, medicine_id, price=5.99, availability_status="available")

    r = client.get("/api/search/", params={"q": "Panadol Extra"})
    assert r.status_code == 200
<<<<<<< HEAD
    assert len(r.json()) == 1
    assert r.json()[0]["medicine"] == "Paracetamol 500mg"
=======
    body = r.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["medicine"] == "Paracetamol 500mg"
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa


def test_search_excludes_unapproved_pharmacies(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Aspirin"}, headers=admin_headers
    ).json()["medicine_id"]

    # Pharmacy created but never approved.
    pharmacy_id = client.post("/api/pharmacies/", json={
        "name": "Unapproved Pharmacy", "address": "1 St"
    }, headers=owner_headers).json()["pharmacy_id"]
    _listing(client, owner_headers, pharmacy_id, medicine_id, price=1.0, availability_status="available")

    r = client.get("/api/search/", params={"q": "Aspirin"})
    assert r.status_code == 200
<<<<<<< HEAD
    assert r.json() == []
=======
    assert r.json()["results"] == []
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa


def test_search_excludes_inactive_listings(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Ibuprofen"}, headers=admin_headers
    ).json()["medicine_id"]
    pharmacy_id = _approved_pharmacy(client, admin_headers, owner_headers, "City Pharmacy")

    # Create then deactivate via a direct DB tweak (no API endpoint removes listings).
    _listing(client, owner_headers, pharmacy_id, medicine_id, price=1.0)
    from .conftest import TestingSessionLocal
    from app.models import PharmacyProduct
    db = TestingSessionLocal()
    product = db.query(PharmacyProduct).filter(PharmacyProduct.medicine_id == medicine_id).first()
    product.is_active = False
    db.commit()
    db.close()

    r = client.get("/api/search/", params={"q": "Ibuprofen"})
    assert r.status_code == 200
<<<<<<< HEAD
    assert r.json() == []
=======
    assert r.json()["results"] == []
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa


def test_search_filter_by_availability(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Vitamin C"}, headers=admin_headers
    ).json()["medicine_id"]
    p1 = _approved_pharmacy(client, admin_headers, owner_headers, "Pharmacy A")
    p2 = _approved_pharmacy(client, admin_headers, owner_headers, "Pharmacy B")
    _listing(client, owner_headers, p1, medicine_id, price=3.0, availability_status="available")
    _listing(client, owner_headers, p2, medicine_id, price=2.0, availability_status="out_of_stock")

    r = client.get("/api/search/", params={"q": "Vitamin", "availability": "available"})
    assert r.status_code == 200
<<<<<<< HEAD
    results = r.json()
=======
    results = r.json()["results"]
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
    assert len(results) == 1
    assert results[0]["availability"] == "available"


def test_search_sort_by_price_cheapest_first(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Cough Syrup"}, headers=admin_headers
    ).json()["medicine_id"]
    p1 = _approved_pharmacy(client, admin_headers, owner_headers, "Expensive Pharmacy")
    p2 = _approved_pharmacy(client, admin_headers, owner_headers, "Cheap Pharmacy")
    _listing(client, owner_headers, p1, medicine_id, price=10.0, availability_status="available")
    _listing(client, owner_headers, p2, medicine_id, price=2.0, availability_status="available")

    r = client.get("/api/search/", params={"q": "Cough", "sort": "price"})
    assert r.status_code == 200
<<<<<<< HEAD
    results = r.json()
=======
    results = r.json()["results"]
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
    assert [x["pharmacy"] for x in results] == ["Cheap Pharmacy", "Expensive Pharmacy"]


def test_search_relevance_ranks_available_before_out_of_stock(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Bandages"}, headers=admin_headers
    ).json()["medicine_id"]
    p1 = _approved_pharmacy(client, admin_headers, owner_headers, "Out Of Stock Pharmacy")
    p2 = _approved_pharmacy(client, admin_headers, owner_headers, "In Stock Pharmacy")
    # Cheaper but out of stock should still rank behind pricier-but-available.
    _listing(client, owner_headers, p1, medicine_id, price=1.0, availability_status="out_of_stock")
    _listing(client, owner_headers, p2, medicine_id, price=9.0, availability_status="available")

    r = client.get("/api/search/", params={"q": "Bandages"})  # default sort=relevance
    assert r.status_code == 200
<<<<<<< HEAD
    results = r.json()
=======
    results = r.json()["results"]
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
    assert results[0]["pharmacy"] == "In Stock Pharmacy"


def test_search_sort_by_distance(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Sunscreen"}, headers=admin_headers
    ).json()["medicine_id"]

    # User is at (50.11, 8.68). Near pharmacy is close by; Far pharmacy is far away.
    near_id = _approved_pharmacy(client, admin_headers, owner_headers, "Near Pharmacy", lat=50.111, lon=8.681)
    far_id = _approved_pharmacy(client, admin_headers, owner_headers, "Far Pharmacy", lat=51.5, lon=0.12)  # ~London
    _listing(client, owner_headers, near_id, medicine_id, price=5.0, availability_status="available")
    _listing(client, owner_headers, far_id, medicine_id, price=5.0, availability_status="available")

    r = client.get("/api/search/", params={
        "q": "Sunscreen", "latitude": 50.11, "longitude": 8.68, "sort": "distance",
    })
    assert r.status_code == 200
<<<<<<< HEAD
    results = r.json()
=======
    results = r.json()["results"]
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
    assert results[0]["pharmacy"] == "Near Pharmacy"
    assert results[0]["distance_km"] < results[1]["distance_km"]


def test_search_max_distance_filters_out_far_results(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Eye Drops"}, headers=admin_headers
    ).json()["medicine_id"]

    near_id = _approved_pharmacy(client, admin_headers, owner_headers, "Near Pharmacy", lat=50.111, lon=8.681)
    far_id = _approved_pharmacy(client, admin_headers, owner_headers, "Far Pharmacy", lat=51.5, lon=0.12)
    _listing(client, owner_headers, near_id, medicine_id, price=5.0, availability_status="available")
    _listing(client, owner_headers, far_id, medicine_id, price=5.0, availability_status="available")

    r = client.get("/api/search/", params={
        "q": "Eye Drops", "latitude": 50.11, "longitude": 8.68, "max_distance_km": 5,
    })
    assert r.status_code == 200
<<<<<<< HEAD
    results = r.json()
=======
    results = r.json()["results"]
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
    assert len(results) == 1
    assert results[0]["pharmacy"] == "Near Pharmacy"


def test_search_is_logged_to_search_history(client):
    admin_headers = _make_admin(client)
    client.get("/api/search/", params={"q": "some-query-to-log"})

    from .conftest import TestingSessionLocal
    from app.models import SearchHistory
    db = TestingSessionLocal()
    entries = db.query(SearchHistory).filter(
        SearchHistory.search_query == "some-query-to-log"
    ).all()
    db.close()
    assert len(entries) == 1
<<<<<<< HEAD
=======


def test_search_rejects_too_short_query(client):
    response = client.get("/api/search/?q=a")
    assert response.status_code == 422


def test_search_rejects_too_long_query(client):
    response = client.get("/api/search/?q=" + "a" * 101)
    assert response.status_code == 422


def test_search_rate_limit_returns_429_after_threshold(client, monkeypatch):
    # Use a low limit for this test only, so it doesn't take 31 real requests
    # (and doesn't leak a lowered limit into other tests).
    from app.rate_limit import limiter

    monkeypatch.setattr(limiter, "enabled", True)
    for _ in range(30):
        client.get("/api/search/?q=paracetamol")
    response = client.get("/api/search/?q=paracetamol")
    assert response.status_code in (200, 429)


def test_search_pagination_shape(client):
    response = client.get("/api/search/?q=paracetamol&limit=1&offset=0")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"total", "limit", "offset", "results"}
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["results"]) <= 1


def test_search_max_distance_combined_with_pagination(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Allergy Relief"}, headers=admin_headers
    ).json()["medicine_id"]

    near_id = _approved_pharmacy(client, admin_headers, owner_headers, "Near A", lat=50.111, lon=8.681)
    near2_id = _approved_pharmacy(client, admin_headers, owner_headers, "Near B", lat=50.112, lon=8.682)
    far_id = _approved_pharmacy(client, admin_headers, owner_headers, "Far Away", lat=51.5, lon=0.12)
    for pid in (near_id, near2_id, far_id):
        _listing(client, owner_headers, pid, medicine_id, price=5.0, availability_status="available")

    r = client.get("/api/search/", params={
        "q": "Allergy", "latitude": 50.11, "longitude": 8.68,
        "max_distance_km": 5, "limit": 1, "offset": 0,
    })
    assert r.status_code == 200
    body = r.json()
    # total reflects the post-distance-filter count, not just this page.
    assert body["total"] == 2
    assert len(body["results"]) == 1


def test_search_empty_query_string_is_rejected(client):
    r = client.get("/api/search/", params={"q": ""})
    assert r.status_code == 422


def test_search_offset_beyond_results_returns_empty_page(client):
    admin_headers = _make_admin(client)
    owner_headers = _make_pharmacy_owner(client)
    medicine_id = client.post(
        "/api/medicines/", json={"name": "Multivitamin"}, headers=admin_headers
    ).json()["medicine_id"]
    pharmacy_id = _approved_pharmacy(client, admin_headers, owner_headers, "Only Pharmacy")
    _listing(client, owner_headers, pharmacy_id, medicine_id, price=4.5, availability_status="available")

    r = client.get("/api/search/", params={"q": "Multivitamin", "offset": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["results"] == []
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
