#!/bin/sh
# Waits for the database to accept connections before starting the app.
set -e

echo "Waiting for database..."

python - <<'PYEOF'
import os
import sys
import time

import psycopg2

url = os.environ.get("DATABASE_URL", "")
if not url.startswith("postgresql"):
    print("Non-Postgres DATABASE_URL detected, skipping wait.")
    sys.exit(0)

dsn = url.replace("postgresql+psycopg2", "postgresql")

for attempt in range(30):
    try:
        conn = psycopg2.connect(dsn)
        conn.close()
        print("Database is ready.")
        sys.exit(0)
    except psycopg2.OperationalError:
        print(f"Database not ready yet (attempt {attempt + 1}/30)...")
        time.sleep(1)

print("Database never became ready, exiting.")
sys.exit(1)
PYEOF

echo "Starting application..."
exec "$@"
