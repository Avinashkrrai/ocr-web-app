# =============================================================================
# Stage 1: Build the React frontend
# =============================================================================
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# =============================================================================
# Stage 2: Compile C++ OCR engine (discarded after .so is copied)
# =============================================================================
FROM python:3.10-slim AS engine-build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake pkg-config \
    libtesseract-dev libleptonica-dev pybind11-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY engine/ ./engine/
RUN cd engine && mkdir -p build && cd build \
    && cmake .. -DPYTHON_EXECUTABLE=$(which python3) \
    && make -j$(nproc)

# =============================================================================
# Stage 3: Lean runtime (no build tools)
# =============================================================================
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy compiled C++ engine from build stage
COPY --from=engine-build /app/engine/build/ocr_engine*.so /app/engine/build/

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt gunicorn

# Copy application code
COPY backend/ ./backend/
COPY finetune/ ./finetune/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

RUN mkdir -p /app/backend/data/uploads /app/backend/data/corrections

ENV PYTHONPATH=/app/engine/build
ENV PYTHONUNBUFFERED=1

CMD ["/app/start.sh"]
