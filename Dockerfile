# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Production Static Server
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies required by RapidOCR and ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy project files: backend code, exact seeded database, uploads, storage, and root brand images
COPY backend/ /app/backend/
COPY aicte.db /app/aicte.db
COPY uploads/ /app/uploads/
COPY storage/ /app/storage/
COPY *.png *.jpg *.jpeg /app/

# Copy built frontend distribution from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Make /app directory fully writable so SQLite (aicte.db) and /uploads work in non-root cloud containers (Hugging Face / Render)
RUN chmod -R 777 /app

ENV PYTHONPATH=/app
ENV PORT=7860

EXPOSE 7860

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]

