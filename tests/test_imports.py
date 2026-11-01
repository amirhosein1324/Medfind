import io

from openpyxl import Workbook

from app.ingest import catalog, sheet
from tests.conftest import TestingSessionLocal


def test_sheet_parsing_variants():
    csv_ = b"Medicine;Price;Stock\nParacetamol 500mg;1.234,50;0\nIbuprofen;5,4;12\n;3;1\nX;abc;1\n"
    rows = sheet.parse_sheet("s.csv", csv_)
    assert str(rows[0]["price"]) == "1234.50" and rows[0]["status"] == "out_of_stock"
    assert str(rows[1]["price"]) == "5.4" and rows[1]["status"] == "available"
    assert rows[2]["error"] and rows[3]["error"]


def test_sheet_requires_columns():
    import pytest
    with pytest.raises(sheet.SheetError):
        sheet.parse_sheet("s.csv", b"foo,bar\n1,2\n")
    with pytest.raises(sheet.SheetError):
        sheet.parse_sheet("s.pdf", b"x")


def test_catalog_csv_and_openfda_mapping():
    db = TestingSessionLocal()
    try:
        csv_ = b"name,generic_name,aliases,prescription_required\nTestol 10mg,Testolam,Testo|T10,yes\n"
        assert catalog.from_csv(db, csv_)["created"] == 1
        assert catalog.from_csv(db, csv_)["existing"] == 1
    finally:
        db.close()
    kw = catalog.openfda_record({"brand_name": "ADVIL", "generic_name": "IBUPROFEN", "dosage_form": "TABLET",
                                 "product_type": "HUMAN OTC DRUG", "active_ingredients": [{"name": "IBUPROFEN", "strength": "200 mg/1"}]})
    assert kw["name"] == "Advil 200 mg/1" and kw["rx"] is False and kw["generic"] == "Ibuprofen"


def _owner(client):
    client.post("/api/users/", json={"full_name": "O", "email": "imp@x.com", "password": "Passw0rd!x", "role": "pharmacy_owner"})
    t = client.post("/api/auth/login", data={"username": "imp@x.com", "password": "Passw0rd!x"}).json()["access_token"]
    h = {"Authorization": f"Bearer {t}"}
    pid = client.post("/api/pharmacies/", json={"name": "P", "address": "A"}, headers=h).json()["pharmacy_id"]
    return h, pid


def test_import_endpoint(client):
    db = TestingSessionLocal()
    catalog.upsert_medicine(db, name="Importol 5mg", aliases=["Impo"])
    catalog.upsert_medicine(db, name="Otherol", barcode="123456")
    db.commit(); db.close()
    h, pid = _owner(client)

    body = b"medicine,price,status,stock\nImportol 5mg,2.5,available,10\nimpo,3,,\nGhostin,1,available,1\n"
    r = client.post(f"/api/pharmacies/{pid}/import", headers=h, files={"file": ("s.csv", body)})
    out = r.json()
    assert r.status_code == 200 and out["created"] == 1 and out["skipped"] == 2  # alias row = duplicate, Ghostin unmatched

    wb = Workbook(); ws = wb.active
    ws.append(["Barcode", "Price", "Stock"]); ws.append(["123456", 7.75, 3]); ws.append(["", None, None])
    buf = io.BytesIO(); wb.save(buf)
    r = client.post(f"/api/pharmacies/{pid}/import", headers=h, files={"file": ("s.xlsx", buf.getvalue())})
    assert r.json()["created"] == 1

    again = client.post(f"/api/pharmacies/{pid}/import", headers=h,
                        files={"file": ("s.csv", b"medicine,price\nImportol 5mg,2.9\n")}).json()
    assert again["updated"] == 1
    hist = client.get(f"/api/pharmacies/{pid}/updates", headers=h).json()
    assert hist and hist[0]["new_price"] == "2.90" or float(hist[0]["new_price"]) == 2.9


def test_import_requires_ownership(client):
    h, pid = _owner(client)
    client.post("/api/users/", json={"full_name": "Z", "email": "z@x.com", "password": "Passw0rd!x", "role": "pharmacy_owner"})
    t = client.post("/api/auth/login", data={"username": "z@x.com", "password": "Passw0rd!x"}).json()["access_token"]
    r = client.post(f"/api/pharmacies/{pid}/import", headers={"Authorization": f"Bearer {t}"},
                    files={"file": ("s.csv", b"medicine,price\nA,1\n")})
    assert r.status_code == 403


def test_admin_catalog_import_endpoint(client):
    from app.models import User
    client.post("/api/users/", json={"full_name": "A", "email": "adm@x.com", "password": "Passw0rd!x"})
    db = TestingSessionLocal(); db.query(User).filter(User.email == "adm@x.com").update({"role": "admin"}); db.commit(); db.close()
    t = client.post("/api/auth/login", data={"username": "adm@x.com", "password": "Passw0rd!x"}).json()["access_token"]
    r = client.post("/api/medicines/import", headers={"Authorization": f"Bearer {t}"},
                    files={"file": ("m.csv", b"name,generic_name\nZedol 1mg,Zedolam\n")})
    assert r.json()["created"] == 1
    assert client.post("/api/medicines/import", files={"file": ("m.csv", b"name\nA\n")}).status_code == 401
