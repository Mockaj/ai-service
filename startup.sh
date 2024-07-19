#!/bin/sh

# Wait for DB to start
sleep 5

# Conditionally seed Elastic
if [ "$RUN_TESTS" != "true" ]; then
  python -m app.db.seed_elastic
fi

# Run FastAPI application with Uvicorn on port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run the command provided by the Dockerfile
exec "$@"
