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
# Stage 2: Build the C++ OCR engine + run the Python backend
# =============================================================================
FROM python:3.10-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libtesseract-dev \
    libleptonica-dev \
    pybind11-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    nginx \
    curl \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build C++ OCR engine
COPY engine/ ./engine/
RUN cd engine \
    && mkdir -p build && cd build \
    && cmake .. -DPYTHON_EXECUTABLE=$(which python3) \
    && make -j$(nproc)

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt gunicorn

# Copy backend code
COPY backend/ ./backend/

# Copy fine-tuning scripts
COPY finetune/ ./finetune/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Copy Nginx template and startup script
COPY nginx.conf.template /app/nginx.conf.template
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create data directories
RUN mkdir -p /app/backend/data/uploads /app/backend/data/corrections

ENV PYTHONPATH=/app/engine/build
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT:-80}

CMD ["/app/start.sh"]
