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

# Create simple FastAPI wrapper
RUN mkdir -p /app
WORKDIR /app

COPY api.py /app/api.py

# Expose port
EXPOSE 8080

# Run the API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
