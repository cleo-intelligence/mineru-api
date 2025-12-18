# MinerU API - CPU-only Dockerfile for Render
# Uses the built-in mineru-api server from the official package

FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV MINERU_MODEL_SOURCE=huggingface

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install uv for faster package installation
RUN pip install --upgrade pip uv

# Install MinerU with core functionality (CPU-only)
RUN uv pip install --system -U "mineru[core]"

# Download models during build (takes time but speeds up runtime)
RUN mineru-models-download -s huggingface -m all || echo "Model download completed with warnings"

# Port configuration (Render sets PORT env var)
ENV PORT=8000
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
  CMD curl -f http://localhost:${PORT}/docs || exit 1

# Use the built-in mineru-api server
CMD mineru-api --host 0.0.0.0 --port ${PORT}
