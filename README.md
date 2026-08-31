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

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # edit SECRET_KEY before deploying anywhere real
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API docs (Swagger UI), which
includes an "Authorize" button that works with the login endpoint below.

## 2a. Running Tests

```bash
pytest
```

The 45-test suite runs against an isolated, disposable SQLite database (not
your real Postgres one) via a `DATABASE_URL` override in `tests/conftest.py`,
so it needs no external services and never touches production data. It covers:

- registration, login, and JWT validation (`tests/test_users_auth.py`)
- role-based access to the medicine catalog and categories (`tests/test_medicines.py`)
- pharmacy approval workflow, ownership checks, and the `pharmacy_updates`
  audit trail (`tests/test_pharmacies.py`)
- the core search endpoint: name/generic/brand/alias matching, availability
  filtering, price/relevance/distance sorting, and search-history logging
  (`tests/test_search.py`)

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
GET /api/search/?q=paracetamol&limit=10&offset=20
```

Responses are now paginated: `{"total": <int>, "limit": <int>, "offset": <int>, "results": [...]}`. Default `limit` is 20 (max 100).

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

These are called out explicitly because they matter before this goes live.
Status of each as of this iteration:

- [x] **Migrations**: Alembic is now wired up (`migrations/`), pointed at the
  app's own `Settings`/`Base` so it can't drift from the models. Run
  `alembic upgrade head` instead of relying on `create_all()` in production.
  `create_all()` is left in `main.py` for zero-friction local dev only.
- [ ] **Secrets**: set a strong, random `SECRET_KEY` in `.env`; never commit `.env`.
- [x] **Rate limiting / input size limits**: `/api/search` is capped at
  30 requests/minute per client IP (slowapi) and `q` is bounded to 2-100
  characters.
- [x] **HTTPS**: the app itself is protocol-agnostic and adds baseline
  security response headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`) via middleware. TLS termination still belongs at the
  reverse proxy / load balancer in front of it (nginx, Caddy, or your
  cloud provider's LB) — this app does not terminate TLS itself.
- [ ] Consider a real search backend (e.g. Postgres full-text search or
  Elasticsearch/Meilisearch) if the `ilike` matching in `search.py` doesn't
  scale or isn't fuzzy enough — the proposal's "Smart Search" section
  (typo tolerance, relevance ranking) is a natural next iteration here.
