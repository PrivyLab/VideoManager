# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Copy package descriptors and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy source and build production bundle
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Backend
# ==========================================
FROM python:3.11-slim

# Install system dependencies (ffmpeg is essential for video muxing/merging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/app/storage/videos

# Install Python requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Copy compiled frontend from Stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Default directories for persistent video storage
RUN mkdir -p /app/storage/videos /app/storage/thumbnails /app/storage/temp_chunks

EXPOSE 8000

# Run uvicorn server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

