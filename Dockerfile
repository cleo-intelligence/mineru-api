# MinerU API - Build from PyPI (no ghcr.io auth required)
FROM python:3.10-slim

# Install system dependencies for OpenCV and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libgomp1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

# Install MinerU from PyPI
RUN pip install --no-cache-dir \
    magic-pdf[full] \
    fastapi \
    uvicorn \
    python-multipart

# Create app directory
RUN mkdir -p /app
WORKDIR /app

COPY api.py /app/api.py

# Copy MinerU configuration file (required by magic-pdf)
COPY magic-pdf.json /root/magic-pdf.json

# Expose port (Render uses PORT env var, default 3000)
EXPOSE 3000

# Use PORT env var (Render sets this to 3000)
ENV PORT=3000

# Run the API using shell to expand $PORT
CMD uvicorn api:app --host 0.0.0.0 --port $PORT
