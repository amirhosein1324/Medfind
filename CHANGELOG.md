# Changelog

## Unreleased (this iteration)

Follows through on the "Production Notes" roadmap from the initial README:

- Alembic migrations, replacing bare `create_all()` for schema changes.
- Rate limiting (30 req/min) and query-length validation on `/api/search`.
- Baseline security response headers + configurable CORS.
- Structured logging with per-request correlation IDs.
- `/health` and `/version` endpoints for uptime monitoring.
- Paginated search responses (`limit`/`offset`, `total` count).
- `SECRET_KEY` safety check: refuses to boot with the default key when
  `DEBUG=false`.
- Dockerfile + docker-compose for containerized local dev.
- GitHub Actions CI running the full pytest suite on every push/PR.
- Additional test coverage: pagination edge cases, JWT edge cases, and
  unit tests for the distance/sorting helpers.

## 1.0.0 — initial release

- FastAPI + SQLAlchemy backend implementing the 8-table proposal schema.
- JWT auth with customer/pharmacy_owner/admin roles.
- Core search endpoint (name/generic/brand/alias matching, distance and
  price sorting, search history logging).
- 45-test pytest suite against an isolated SQLite database.
