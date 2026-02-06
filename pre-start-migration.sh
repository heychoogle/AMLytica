#!/bin/bash

echo "Waiting for postgres..."

until nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

echo "Running migrations..."
alembic upgrade head

echo "Migrations complete. Starting application..."
exec "$@"