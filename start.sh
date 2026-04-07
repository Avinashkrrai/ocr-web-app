#!/bin/bash
set -e

export PORT="${PORT:-80}"

echo "Starting OCR Web Application on port $PORT..."

cd /app/backend
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-1} \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
