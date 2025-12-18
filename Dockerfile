# MinerU API - CPU-only Dockerfile for Render
# Based on official MinerU installation docs

FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Install MinerU core (CPU-only, no vLLM)
RUN uv pip install --system -U "mineru[core]"

# Download models (this will take some time during build)
RUN python -c "from magic_pdf.model.doc_analyze_by_custom_model import ModelSingleton; ModelSingleton().get_model(False, False)"

# Install FastAPI and dependencies for the API server
RUN uv pip install --system fastapi uvicorn python-multipart

# Copy application files
COPY app.py ./
COPY magic-pdf.json /root/magic-pdf.json

# Port configuration
ENV PORT=3000
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the API server
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT}
