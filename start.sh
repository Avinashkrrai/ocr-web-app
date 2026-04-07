#!/bin/bash
set -e

export PORT="${PORT:-10000}"

echo "=== OCR Web App Startup ==="
echo "PORT=$PORT  WORKERS=${WORKERS:-1}  LANG=${OCR_LANG:-eng}"
echo ""

# Verify critical dependencies load
echo "Checking dependencies..."
cd /app/backend

python3 -c "
import sys
sys.path.insert(0, '/app/engine/build')
print('  Python:', sys.version.split()[0])

try:
    import ocr_engine
    e = ocr_engine.OCREngine()
    ok = e.init()
    print('  C++ OCR engine: OK' if ok else '  C++ OCR engine: INIT FAILED')
except Exception as ex:
    print(f'  C++ OCR engine: FAILED - {ex}')

try:
    from app.main import app
    print('  FastAPI app: OK')
except Exception as ex:
    print(f'  FastAPI app: FAILED - {ex}')
"

echo ""
echo "Starting Gunicorn on port $PORT..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-1} \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
