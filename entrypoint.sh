#!/bin/sh

# Wait for DB (simple sleep loop, or use wait-for-it)
# Using a simple python check or just sleep for simplicity in this demo
echo "Waiting for database..."
sleep 5

# Run migration (create tables if not exist)
# main.py does create_all on import/start, but let's be explicit if needed.
# Since uvicorn runs main:app, formatting main.py execution triggers create_all.
# We can just run the seed script which imports models/database and thus triggers table creation too.

echo "Running migrations and seeding..."
python seed_users.py

echo "Starting Server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
