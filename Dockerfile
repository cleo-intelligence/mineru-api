# MinerU API - Build from PyPI with persistent disk support
FROM python:3.10-slim

# Install system dependencies for OpenCV, PDF processing, and OCR
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
    tesseract-ocr-eng \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# Install MinerU from PyPI
RUN pip install --no-cache-dir \
    magic-pdf[full] \
    fastapi \
    uvicorn \
    python-multipart

# Create app directory
RUN mkdir -p /app
WORKDIR /app

# Copy application files
COPY api.py /app/api.py
COPY download_models.py /app/download_models.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port (Render uses PORT env var, default 3000)
EXPOSE 3000

# Use PORT env var (Render sets this to 3000)
ENV PORT=3000
ENV MINERU_MODELS_DIR=/root/cache/models

# Run startup script
CMD ["/app/start.sh"]
