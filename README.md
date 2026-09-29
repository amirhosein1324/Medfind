# MedFind Backend

FastAPI + SQLAlchemy backend for the MedFind medicine search and pharmacy
comparison platform, implementing the 8-table database design from the
project proposal plus the authentication, authorization, and audit-trail
features the proposal calls out as needed for production.

## 1. Project Structure

```
MedFind/
├── app/
│   ├── main.py            # FastAPI app + router registration
│   ├── config.py          # Settings loaded from .env
│   ├── database.py        # Engine / session / Base
│   ├── models.py          # All 8 SQLAlchemy tables
│   ├── schemas.py         # Pydantic request/response models
│   ├── security.py        # Password hashing, JWT, role-based auth
│   ├── utils.py            # Haversine distance calculation
│   └── routers/
│       ├── auth.py         # POST /api/auth/login
│       ├── users.py        # Registration, profile
│       ├── medicines.py    # Medicine catalog, categories, aliases
│       ├── pharmacies.py   # Pharmacy management, product listings
│       └── search.py       # Core search + ranking endpoint
├── requirements.txt
├── .env.example
└── README.md
```

## 2. Setup

### Option A: Docker (recommended)

```bash
docker compose up --build
```

This starts Postgres and the API together. The API waits for Postgres to be
ready before starting (see `entrypoint.sh`). Once running, open
http://127.0.0.1:8000/docs. Data persists in a named volume
(`medfind_pgdata`) across restarts.

Set a real secret before deploying anywhere beyond your own machine:
```bash
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") docker compose up --build
```

### Option B: Run directly with Python

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # edit SECRET_KEY before deploying anywhere real
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API docs (Swagger UI), which
includes an "Authorize" button that works with the login endpoint below.

## 2b. Database Stress Test (Docker)

A database-only stress test (no API involved) is included as a separate
compose service. It doesn't start with a normal `docker compose up`.

```bash
# default: 10 concurrent connections, 20 seconds, 80% reads / 20% writes
docker compose --profile stress run --rm stress

# heavier load, via environment variables:
STRESS_CONCURRENCY=50 STRESS_DURATION=60 docker compose --profile stress run --rm stress
# Windows PowerShell:
$env:STRESS_CONCURRENCY=50; $env:STRESS_DURATION=60; docker compose --profile stress run --rm stress
```

It reports throughput (ops/sec) and latency (avg/p50/p95/p99/max) for reads
and writes. It seeds its own test rows (names start with `StressMed-`).
Run `docker compose down -v` to wipe the database volume afterward.

## 2a. Running Tests

Two test suites are included:

```bash
pip install -r requirements-dev.txt

# Fast unit tests — run against disposable SQLite, no setup needed
pytest tests/ --ignore=tests/test_postgres.py

# PostgreSQL integration tests — run against a REAL Postgres instance
# Start Postgres first (`docker compose up db`, or a local install), then:
pytest tests/test_postgres.py -v

# Or just run everything — test_postgres.py auto-skips (not fails) if
# Postgres isn't reachable, so this is always safe to run:
pytest
```

**`tests/test_users_auth.py`, `test_medicines.py`, `test_pharmacies.py`, `test_search.py`**
(45 tests) — cover registration, JWT login, role-based access, pharmacy
ownership checks, the audit trail, and the full search/ranking/distance
logic. Run against SQLite for speed.

**`tests/test_postgres.py`** (12 tests) — connects to a real PostgreSQL
database and verifies things SQLite can't: the native `user_role` and
`availability_status` ENUM types actually exist, foreign-key and unique
constraints are enforced at the database level (not just in application
code), NUMERIC price precision is preserved, and a full register → login →
create → approve → list → update → search flow works end-to-end against
Postgres specifically. If Postgres isn't running, these 12 tests are
skipped with a clear message rather than failing the whole suite.

By default it looks for Postgres at
`postgresql+psycopg2://medfind:medfind@localhost:5432/medfind` (matching
`docker-compose.yml`). Point it elsewhere with:
```bash
TEST_DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname pytest tests/test_postgres.py
```

By default this runs on **PostgreSQL**. Create the database and role once:

```bash
sudo -u postgres psql -c "CREATE ROLE medfind WITH LOGIN PASSWORD 'medfind';"
sudo -u postgres psql -c "CREATE DATABASE medfind OWNER medfind;"
```

Then point `.env` at it (this is already the default in `.env.example`):
```
DATABASE_URL=postgresql+psycopg2://medfind:medfind@localhost:5432/medfind
```

Adjust host/port/user/password for a hosted Postgres instance (RDS, Supabase,
Render, etc.) — same URL format.

If you'd rather not stand up Postgres for local testing, SQLite works with
zero setup — just swap `DATABASE_URL` to `sqlite:///./medfind.db` in `.env`.

## 3. Data Model

The 8 tables from the proposal's database design section:

| Table | Purpose |
|---|---|
| `users` | Customers, pharmacy owners, and admins (role-based) |
| `medicine_categories` | Optional grouping for medicines |
| `medicines` | Core medicine records (name, generic, brand, dosage, form...) |
| `medicine_aliases` | Alternate names/spellings so search finds a medicine under any name |
| `pharmacies` | Pharmacy profile + location, subject to admin approval |
| `pharmacy_products` | The join table: one row per (pharmacy, medicine) — price, stock, availability |
| `pharmacy_updates` | Audit trail: every price/stock/availability change is logged here |
| `search_history` | Logged queries, for analytics/personalization |

One medicine can be listed by many pharmacies and one pharmacy can list many
medicines; `pharmacy_products` is the connecting entity, exactly as laid out
in the proposal's ER sketch.

## 4. Auth & Roles

Three roles, matching the proposal's "Target Users" section:

- **customer** — searches, no special permissions.
- **pharmacy_owner** — can create a pharmacy (pending admin approval), and
  manage products/listings for pharmacies they own.
- **admin** — approves pharmacies, manages the medicine catalog/categories/
  aliases, and can act on any pharmacy.

Login flow:

```
POST /api/users/            { full_name, email, password, phone?, role }   -> register (customer|pharmacy_owner)
POST /api/auth/login         (form fields: username=email, password)        -> { access_token }
```

Send `Authorization: Bearer <access_token>` on subsequent requests.
Admin accounts aren't self-service — create the first one directly in the
database (or via a one-off script) and promote further admins from there.

Every pharmacy-listing update is authorization-checked (must be the owning
pharmacy_owner, or an admin) and written to `pharmacy_updates` with the
before/after values — this is what the proposal's "Data Accuracy" and
"Security Considerations" sections ask for.

## 5. Core Search Endpoint

```
GET /api/search/?q=paracetamol
GET /api/search/?q=paracetamol&latitude=50.11&longitude=8.68&sort=distance
GET /api/search/?q=paracetamol&max_distance_km=5&availability=available&sort=price
```

- Matches medicine name, generic name, brand name, **and aliases** — so a
  pharmacy calling something "Panadol Extra" still surfaces a "Paracetamol"
  search, addressing the proposal's "different pharmacies use different
  names" problem.
- Only returns listings from **approved** pharmacies and **active** listings.
- `sort=relevance` (default) ranks by availability, then price, then recency.
- `sort=distance` needs `latitude`/`longitude`; distance is a real haversine
  calculation, not a placeholder.
- Every search is logged to `search_history` for future personalization.

## 6. Example Requests

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Alice","email":"alice@example.com","password":"supersecret1","role":"pharmacy_owner"}'

# Login
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -d "username=alice@example.com&password=supersecret1"

# Search
curl "http://127.0.0.1:8000/api/search/?q=paracetamol&sort=price"
```

## 7. Production Notes

These are called out explicitly because they matter before this goes live —
they're not yet automated here:

- **Migrations**: `Base.metadata.create_all()` (used at startup) is fine for
  development only. Introduce **Alembic** for real schema migrations.
- **Secrets**: set a strong, random `SECRET_KEY` in `.env`; never commit `.env`.
- **Rate limiting / input size limits** on the search endpoint before public launch.
- **HTTPS** termination in front of the API in any real deployment.
- Consider a real search backend (e.g. Postgres full-text search or
  Elasticsearch/Meilisearch) if the `ilike` matching in `search.py` doesn't
  scale or isn't fuzzy enough — the proposal's "Smart Search" section
  (typo tolerance, relevance ranking) is a natural next iteration here.
