# ==========================================
# Stage 1: Build React Frontend
# ==========================================
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Build Python Backend & Serve
# ==========================================
FROM python:3.10-slim AS backend-runner
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY backend/app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install sentence-transformers & faiss manually to ensure caching
RUN pip install --no-cache-dir sentence-transformers faiss-cpu

# Copy app code
COPY backend/app/ ./backend/app/
COPY ai_services/ ./ai_services/

# Copy built frontend assets into FastAPI static files directory
COPY --from=frontend-builder /app/frontend/dist ./backend/app/static

# Set environment
ENV PYTHONPATH=/app
ENV PORT=8085

EXPOSE 8085

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8085/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8085"]
