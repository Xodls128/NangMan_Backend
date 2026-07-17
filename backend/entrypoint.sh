#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python <<'PY'
import os, time, sys
import psycopg

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "5432"))
name = os.environ["DB_NAME"]
user = os.environ["DB_USER"]
password = os.environ["DB_PASSWORD"]

for i in range(60):
    try:
        with psycopg.connect(
            host=host, port=port, dbname=name, user=user, password=password, connect_timeout=3
        ):
            print("PostgreSQL is ready.")
            sys.exit(0)
    except Exception as exc:
        print(f"  retry {i + 1}/60: {exc}")
        time.sleep(2)

print("PostgreSQL did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Daphne..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
