# MinerU API - Use pre-built image for reliability
# This avoids build issues with Poetry/pip on constrained memory environments
FROM jianjungki/mineru-api:latest

# Override the port to use PORT env variable (Render provides this)
ENV PORT=3000

# Health check for Render
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose the port
EXPOSE ${PORT}

# Start uvicorn with configurable port
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT}
