# syntax=docker/dockerfile:1
# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Multi-stage production container for CARINA Core + Go Hardware Gateway

# --- Stage 1: Compile Go Hardware Gateway ---
FROM golang:1.22-alpine AS builder-go
WORKDIR /app/src_go

COPY src_go/go.mod src_go/go.sum* ./
RUN go mod download || true

COPY src_go/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/bin/carina-go ./cmd/gateway

# --- Stage 2: Python 3.12 Runtime ---
FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="CARINA Core" \
      org.opencontainers.image.description="Adaptive AI Traffic Network Architecture" \
      org.opencontainers.image.vendor="Noxfort Systems" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    CARINA_DB_TYPE=sqlite \
    CARINA_CONTAINER_MODE=1

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxkbcommon0 \
    libcairo2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user for security
RUN groupadd -g 10001 carina && \
    useradd -u 10001 -g carina -s /bin/bash -m carina

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy compiled Go gateway binary
COPY --from=builder-go /app/bin/carina-go /app/bin/carina-go
RUN chmod +x /app/bin/carina-go

# Copy application source code and configurations
COPY config/ /app/config/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini
COPY src/ /app/src/
COPY carina.py /app/carina.py

# Set proper ownership
RUN chown -R carina:carina /app
USER carina

# Healthcheck to verify system integrity
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import src; print('CARINA OK')" || exit 1

EXPOSE 8080 8765 50051

ENTRYPOINT ["python", "carina.py", "--headless"]
