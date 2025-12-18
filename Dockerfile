# MinerU API - Custom Dockerfile with OpenCV dependencies
# Fixes: ImportError: libgthread-2.0.so.0: cannot open shared object file

FROM ghcr.io/opendatalab/mineru:latest

# Install missing system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Expose the API port
EXPOSE 8080

# Default command (from base image)
CMD ["mineru-api", "--host", "0.0.0.0", "--port", "8080"]
