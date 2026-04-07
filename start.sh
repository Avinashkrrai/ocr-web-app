#!/bin/bash
set -e

# Railway (and similar platforms) set PORT dynamically; default to 80
export PORT="${PORT:-80}"

echo "Starting OCR Web Application on port $PORT..."

# Generate Nginx config from template with the correct PORT
envsubst '${PORT}' < /app/nginx.conf.template > /etc/nginx/nginx.conf

# Start the FastAPI backend with Gunicorn
cd /app/backend
gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-1} \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - &

BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        echo "Backend ready."
        break
    fi
    sleep 1
done

# Start Nginx
echo "Starting Nginx on port $PORT..."
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "Application is live on port $PORT"

wait -n $BACKEND_PID $NGINX_PID
exit $?
