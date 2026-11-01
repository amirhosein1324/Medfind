"""
Standalone PostgreSQL stress test for MedFind.

Hits the REAL database directly with concurrent workers doing a realistic
mix of reads (search-style queries) and writes (the pharmacy_updates path,
which is the hottest write path in the app) — no FastAPI/HTTP involved,
just raw DB load. Useful to answer "can Postgres itself handle this
throughput" before layering API/network overhead on top.

Usage:
    python scripts/stress_test_postgres.py
    python scripts/stress_test_postgres.py --duration 30 --concurrency 20
    python scripts/stress_test_postgres.py --url postgresql+psycopg2://user:pass@host:5432/db

Requires the app's tables to already exist (run the app once, or
`docker compose up db` + let the API create tables on first boot).
"""
import argparse
import os
import random
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ---------- Setup: seed a baseline dataset to stress against ----------

def seed_data(engine, num_medicines=50, num_pharmacies=20):
    """Ensure there's enough data in place that reads/writes have something
    realistic to hit. Safe to re-run — only adds data, marked with a run id
    so it's easy to spot in the DB afterward."""
    from app.models import User, Medicine, Pharmacy, PharmacyProduct

    Session = sessionmaker(bind=engine)
    db = Session()

    run_tag = uuid.uuid4().hex[:8]
    print(f"Seeding data (run tag: {run_tag}) ...")

    owner = User(
        full_name="Stress Test Owner",
        email=f"stress-{run_tag}@example.com",
        password_hash="not-a-real-hash",
        role="pharmacy_owner",
    )
    db.add(owner)
    db.flush()

    medicines = [
        Medicine(name=f"StressMed-{run_tag}-{i}", generic_name=f"Generic-{i}")
        for i in range(num_medicines)
    ]
    db.add_all(medicines)
    db.flush()

    pharmacies = [
        Pharmacy(
            owner_user_id=owner.user_id,
            name=f"StressPharmacy-{run_tag}-{i}",
            address=f"{i} Stress St",
            latitude=50.0 + random.random(),
            longitude=8.0 + random.random(),
            is_approved=True,
        )
        for i in range(num_pharmacies)
    ]
    db.add_all(pharmacies)
    db.flush()

    products = []
    for pharmacy in pharmacies:
        for medicine in random.sample(medicines, k=min(10, len(medicines))):
            products.append(PharmacyProduct(
                pharmacy_id=pharmacy.pharmacy_id,
                medicine_id=medicine.medicine_id,
                price=Decimal(str(round(random.uniform(1, 50), 2))),
                availability_status=random.choice(["available", "limited_stock", "out_of_stock"]),
                stock_quantity=random.randint(0, 100),
            ))
    db.add_all(products)
    db.commit()

    product_ids = [p.product_id for p in products]
    medicine_names = [m.name for m in medicines]
    db.close()

    print(f"Seeded {len(medicines)} medicines, {len(pharmacies)} pharmacies, {len(products)} listings.")
    return product_ids, medicine_names


# ---------- Worker operations ----------

def do_read(session, medicine_names):
    """Simulates the core search query: name match + join to pharmacy."""
    name = random.choice(medicine_names)
    query_fragment = name.split("-")[0]  # partial match, like a real user search
    session.execute(text("""
        SELECT pp.product_id, m.name, ph.name, pp.price, pp.availability_status
        FROM pharmacy_products pp
        JOIN medicines m ON m.medicine_id = pp.medicine_id
        JOIN pharmacies ph ON ph.pharmacy_id = pp.pharmacy_id
        WHERE m.name ILIKE :q AND pp.is_active = true AND ph.is_approved = true
        LIMIT 20
    """), {"q": f"%{query_fragment}%"}).fetchall()


def do_write(session, product_ids):
    """Simulates a pharmacy updating price/stock — the hottest write path
    in the real app (POST/PATCH .../products/{id})."""
    product_id = random.choice(product_ids)
    new_price = round(random.uniform(1, 50), 2)
    new_stock = random.randint(0, 100)
    session.execute(text("""
        UPDATE pharmacy_products
        SET price = :price, stock_quantity = :stock, last_updated = now()
        WHERE product_id = :pid
    """), {"price": new_price, "stock": new_stock, "pid": product_id})
    session.commit()


def worker(engine, product_ids, medicine_names, read_ratio, stop_at, results, errors):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        while time.monotonic() < stop_at:
            is_read = random.random() < read_ratio
            start = time.perf_counter()
            try:
                if is_read:
                    do_read(session, medicine_names)
                else:
                    do_write(session, product_ids)
                elapsed_ms = (time.perf_counter() - start) * 1000
                results.append(("read" if is_read else "write", elapsed_ms))
            except Exception as e:
                session.rollback()
                errors.append(str(e))
    finally:
        session.close()


# ---------- Reporting ----------

def percentile(data, pct):
    if not data:
        return 0.0
    data = sorted(data)
    k = (len(data) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(data) - 1)
    if f == c:
        return data[f]
    return data[f] + (data[c] - data[f]) * (k - f)


def report(results, errors, duration):
    if not results:
        print("No operations completed — something is very wrong.")
        return

    all_latencies = [ms for _, ms in results]
    read_latencies = [ms for op, ms in results if op == "read"]
    write_latencies = [ms for op, ms in results if op == "write"]

    total_ops = len(results)
    print("\n" + "=" * 60)
    print("STRESS TEST RESULTS")
    print("=" * 60)
    print(f"Duration:         {duration:.1f}s")
    print(f"Total operations: {total_ops}  ({len(read_latencies)} reads, {len(write_latencies)} writes)")
    print(f"Throughput:       {total_ops / duration:.1f} ops/sec")
    print(f"Errors:           {len(errors)}")
    print("-" * 60)
    print(f"{'':10}{'avg':>10}{'p50':>10}{'p95':>10}{'p99':>10}{'max':>10}   (ms)")
    for label, data in [("all", all_latencies), ("reads", read_latencies), ("writes", write_latencies)]:
        if not data:
            continue
        print(
            f"{label:10}"
            f"{statistics.mean(data):>10.2f}"
            f"{percentile(data, 50):>10.2f}"
            f"{percentile(data, 95):>10.2f}"
            f"{percentile(data, 99):>10.2f}"
            f"{max(data):>10.2f}"
        )
    print("=" * 60)

    if errors:
        print(f"\nFirst 5 errors:")
        for e in errors[:5]:
            print(f"  - {e}")


def main():
    parser = argparse.ArgumentParser(description="Stress test the MedFind PostgreSQL database directly.")
    parser.add_argument("--url", default=os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://medfind:medfind@localhost:5432/medfind"
    ), help="SQLAlchemy database URL")
    parser.add_argument("--duration", type=int, default=20, help="Seconds to run the load for")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent DB connections/workers")
    parser.add_argument("--read-ratio", type=float, default=0.8, help="Fraction of ops that are reads (0-1)")
    parser.add_argument("--skip-seed", action="store_true", help="Skip seeding; reuse whatever data already exists")
    args = parser.parse_args()

    print(f"Target: {args.url}")
    print(f"Concurrency: {args.concurrency} workers | Duration: {args.duration}s | Read ratio: {args.read_ratio}")

    engine = create_engine(args.url, pool_size=args.concurrency + 2, max_overflow=0, pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"\nCould not connect to the database: {e}")
        print("Make sure Postgres is running (`docker compose up db`) and the app has created its tables.")
        sys.exit(1)

    # Make sure the schema exists (safe no-op if the API already created it),
    # so this script also works on a brand-new empty database in Docker.
    from app.database import Base
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    if args.skip_seed:
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        db = Session()
        product_ids = [r[0] for r in db.execute(text("SELECT product_id FROM pharmacy_products")).fetchall()]
        medicine_names = [r[0] for r in db.execute(text("SELECT name FROM medicines")).fetchall()]
        db.close()
        if not product_ids:
            print("No existing data found and --skip-seed was passed. Run without --skip-seed at least once.")
            sys.exit(1)
    else:
        product_ids, medicine_names = seed_data(engine)

    results = []
    errors = []
    stop_at = time.monotonic() + args.duration

    print(f"\nRunning for {args.duration}s ...")
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(worker, engine, product_ids, medicine_names, args.read_ratio, stop_at, results, errors)
            for _ in range(args.concurrency)
        ]
        for f in as_completed(futures):
            f.result()  # re-raise any worker-level exception
    actual_duration = time.monotonic() - start

    report(results, errors, actual_duration)


if __name__ == "__main__":
    main()
