#!/bin/bash
set -e

export PORT="${PORT:-10000}"

echo "=== OCR Web App Startup ==="
echo "PORT=$PORT  WORKERS=${WORKERS:-1}  LANG=${OCR_LANG:-eng}"
echo ""

cd /app/backend

python3 -c "
import sys
sys.path.insert(0, '/app/engine/build')
print('  Python:', sys.version.split()[0])

try:
    import ocr_engine
    print('  C++ OCR engine module: OK')
except Exception as ex:
    print(f'  C++ OCR engine module: FAILED - {ex}')
    sys.exit(1)

try:
    from app.main import app
    print('  FastAPI app: OK')
except Exception as ex:
    print(f'  FastAPI app: FAILED - {ex}')
    sys.exit(1)
"

echo ""
echo "Starting Gunicorn on port $PORT..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS:-1}" \
    --bind "0.0.0.0:$PORT" \
    --timeout 300 \
    --graceful-timeout 120 \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile - \
    --log-level info
