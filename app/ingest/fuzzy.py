"""Typo-tolerant matching.

PostgreSQL: pg_trgm trigram similarity (word_similarity) backed by GIN indexes.
Other databases (SQLite in tests): difflib on the word level, slower but the same idea,
so 'paracetmol' still finds 'Paracetamol' everywhere."""
import difflib
import logging
import re

from sqlalchemy import func, text
from sqlalchemy.orm import Session

log = logging.getLogger("medfind.fuzzy")
MIN_LEN = 4          # shorter queries are too ambiguous to fuzzy-match
PG_THRESHOLD = 0.4   # word_similarity cut-off
PY_THRESHOLD = 0.78  # difflib ratio cut-off


def is_pg(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def ensure_indexes(engine) -> bool:
    """Enable pg_trgm and create trigram GIN indexes. Safe to call on every start."""
    if engine.dialect.name != "postgresql":
        return False
    stmts = ["CREATE EXTENSION IF NOT EXISTS pg_trgm"] + [
        f"CREATE INDEX IF NOT EXISTS ix_{t}_{c}_trgm ON {t} USING gin ({c} gin_trgm_ops)"
        for t, c in (("web_products", "title"), ("web_products", "title_en"), ("web_products", "generic_en"),
                     ("medicines", "name"), ("medicines", "generic_name"), ("medicines", "brand_name"),
                     ("medicine_aliases", "alias_name"))
    ]
    try:
        with engine.begin() as c:
            for s in stmts:
                c.execute(text(s))
        return True
    except Exception as e:  # no permission / extension missing: search still works, just without typo tolerance
        log.warning("pg_trgm unavailable (%s); typo-tolerant search disabled", e)
        return False


def _words(s: str) -> list[str]:
    return re.findall(r"\w{3,}", (s or "").lower())


def _py_match(q: str, value: str) -> float:
    best = 0.0
    for qw in _words(q):
        for w in _words(value):
            best = max(best, difflib.SequenceMatcher(None, qw, w).ratio())
    return best


def similar(db: Session, model, columns, q: str, limit: int = 200) -> list:
    """Rows of `model` whose `columns` look like q, best first."""
    q = (q or "").strip().lower()
    if len(q) < MIN_LEN:
        return []
    cols = [getattr(model, c) for c in columns]
    if is_pg(db):
        try:
            db.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = :t"), {"t": PG_THRESHOLD})
            score = func.greatest(*[func.coalesce(func.word_similarity(q, c), 0) for c in cols])
            return db.query(model).filter(score >= PG_THRESHOLD).order_by(score.desc()).limit(limit).all()
        except Exception as e:
            db.rollback()
            log.warning("fuzzy query failed: %s", e)
            return []
    scored = []
    for row in db.query(model).limit(20000):
        s = max((_py_match(q, getattr(row, c) or "") for c in columns), default=0)
        if s >= PY_THRESHOLD:
            scored.append((s, row))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]]
