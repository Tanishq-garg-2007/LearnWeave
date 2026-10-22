#!/bin/sh
set -e

echo "=== LearnWeave AI Startup ==="

# Run database migrations if database URL is provided
if [ -n "$SYNC_DATABASE_URL" ]; then
    echo "Running Alembic database migrations..."
    cd /app/backend && alembic upgrade head && cd /app || {
        echo "Warning: Alembic migration failed or database unreachable. Proceeding anyway..."
    }
fi

PORT="${PORT:-7860}"
echo "Starting LearnWeave server on port ${PORT}..."
exec python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "$PORT"
