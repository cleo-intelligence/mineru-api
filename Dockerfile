# MinerU API - CPU-only (adapted from official Dockerfile)
# Official uses vllm/vllm-openai which requires GPU
# This version uses python base for CPU-only deployment

FROM python:3.10-slim-bookworm

# Install system dependencies (same as official)
RUN apt-get update && \
    apt-get install -y \
        fonts-noto-core \
        fontconfig \
        libgl1 \
        curl && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install mineru (same as official)
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -U 'mineru[core]' && \
    python3 -m pip cache purge

# Download models (same as official)
RUN mineru-models-download -s huggingface -m all || true

# Environment
ENV MINERU_MODEL_SOURCE=local
ENV PORT=8000

EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:${PORT}/docs || exit 1

# Start API server (official uses CLI, we use API server)
CMD exec mineru-api --host 0.0.0.0 --port ${PORT}
