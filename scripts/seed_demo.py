"""Seed demo data so the web UI has something to show.

    python -m scripts.seed_demo            # uses DATABASE_URL
    docker compose exec api python -m scripts.seed_demo

Creates (idempotent): admin@medfind.test / owner@medfind.test (password
"Passw0rd!demo"), 10 medicines, 8 approved pharmacies around Frankfurt and
a spread of listings with different availability and freshness.
Pass --lat/--lon to centre the pharmacies on your own location.
"""
import argparse
import math
import random
from datetime import datetime, timedelta

from app.database import Base, SessionLocal, engine
from app.models import Medicine, MedicineAlias, Pharmacy, PharmacyProduct, User
from app.security import hash_password

PASSWORD = "Passw0rd!demo"
MEDS = [
    ("Paracetamol 500mg", "Paracetamol", "Panadol", "500mg", "Tablet", False, 4.2, ["Acetaminophen", "Panadol Extra"]),
    ("Paracetamol 1000mg", "Paracetamol", "Dafalgan", "1000mg", "Effervescent tablet", False, 6.1, ["Acetaminophen 1000"]),
    ("Ibuprofen 400mg", "Ibuprofen", "Advil", "400mg", "Tablet", False, 5.4, ["Nurofen"]),
    ("Amoxicillin 500mg", "Amoxicillin", "Amoxil", "500mg", "Capsule", True, 9.8, []),
    ("Cetirizine 10mg", "Cetirizine", "Zyrtec", "10mg", "Tablet", False, 7.3, ["Allergy relief"]),
    ("Omeprazole 20mg", "Omeprazole", "Losec", "20mg", "Capsule", False, 8.9, ["Prilosec"]),
    ("Vitamin D3 1000 IU", "Cholecalciferol", None, "1000 IU", "Softgel", False, 11.5, ["Vitamin D"]),
    ("Salbutamol 100mcg", "Salbutamol", "Ventolin", "100mcg", "Inhaler", True, 12.4, ["Albuterol"]),
    ("Loratadine 10mg", "Loratadine", "Claritin", "10mg", "Tablet", False, 6.7, []),
    ("Metformin 500mg", "Metformin", "Glucophage", "500mg", "Tablet", True, 5.9, []),
]
PHARM = [  # name, address, dx_km, dy_km, hours, verified
    ("Green Cross Pharmacy", "12 Linden Street", 0.7, 0.5, "Mon-Sat 8:00-20:00", True),
    ("Riverside Pharmacy", "48 Quay Road", -1.6, 1.1, "Daily 9:00-21:00", True),
    ("Northgate Apotheke", "3 Northgate Square", 0.3, 3.2, "Mon-Fri 8:30-18:30", True),
    ("Parkview Pharmacy", "210 Park Avenue", 2.9, -1.2, "Daily 7:00-23:00", False),
    ("Old Town Pharmacy", "7 Cobble Lane", -0.4, -0.9, "Mon-Fri 9:00-17:30", True),
    ("Harbor Health Pharmacy", "91 Dockside Way", -4.8, -2.4, "Mon-Sat 8:00-19:00", False),
    ("Westfield Pharmacy", "5 Westfield Mall", -6.5, 1.8, "Daily 10:00-22:00", True),
    ("Central Station Pharmacy", "Platform Level, Central Station", 1.2, -2.0, "Daily 6:00-22:00", True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=50.1109)
    ap.add_argument("--lon", type=float, default=8.6821)
    a = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    rnd = random.Random(7)
    try:
        if db.query(User).filter(User.email == "admin@medfind.test").first():
            print("Demo data already present.")
            return
        admin = User(full_name="Demo Admin", email="admin@medfind.test", password_hash=hash_password(PASSWORD), role="admin")
        owner = User(full_name="Demo Owner", email="owner@medfind.test", password_hash=hash_password(PASSWORD), role="pharmacy_owner")
        db.add_all([admin, owner]); db.flush()

        meds = []
        for name, gen, brand, dose, form, rx, _, aliases in MEDS:
            m = Medicine(name=name, generic_name=gen, brand_name=brand, dosage=dose, form=form, prescription_required=rx)
            m.aliases = [MedicineAlias(alias_name=x, alias_type="brand") for x in aliases]
            db.add(m); meds.append(m)
        db.flush()

        for i, (name, addr, dx, dy, hours, ver) in enumerate(PHARM):
            ph = Pharmacy(
                owner_user_id=owner.user_id, name=name, address=addr, phone=f"+1 555 01{i:02d}", opening_hours=hours,
                latitude=a.lat + dy / 110.574, longitude=a.lon + dx / (111.32 * math.cos(math.radians(a.lat))),
                is_verified=ver, is_approved=True,
            )
            db.add(ph); db.flush()
            for m, spec in zip(meds, MEDS):
                if rnd.random() < 0.2:
                    continue
                roll = rnd.random()
                status = "available" if roll < .55 else "limited_stock" if roll < .75 else "out_of_stock" if roll < .9 else "unknown"
                age = rnd.choice([10, 45, 300, 1200, 2400, 6000])  # minutes
                db.add(PharmacyProduct(
                    pharmacy_id=ph.pharmacy_id, medicine_id=m.medicine_id,
                    price=round(spec[6] * rnd.uniform(.85, 1.25), 2), availability_status=status,
                    stock_quantity=0 if status == "out_of_stock" else rnd.randint(1, 4) if status == "limited_stock" else rnd.randint(8, 60),
                    last_updated=datetime.utcnow() - timedelta(minutes=age),
                ))
        db.commit()
        print(f"Seeded. Log in with admin@medfind.test or owner@medfind.test / {PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
