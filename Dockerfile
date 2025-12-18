# MinerU API - CPU-only Dockerfile for Render
FROM python:3.10-slim-bookworm

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    MINERU_MODEL_SOURCE=huggingface

# System dependencies (single layer, minimal packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Install Python packages
RUN pip install --upgrade pip && \
    pip install uv && \
    uv pip install --system -U "mineru[core]"

# Download models (may take several minutes)
RUN mineru-models-download -s huggingface -m all || true

# Port
ENV PORT=8000
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:${PORT}/docs || exit 1

# Start server
CMD exec mineru-api --host 0.0.0.0 --port ${PORT}
