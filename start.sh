#!/bin/bash
# MinerU API startup script
# Downloads models if missing, creates config, and starts uvicorn

set -e

MODELS_DIR="${MINERU_MODELS_DIR:-/root/cache/models}"
CONFIG_PATH="/root/magic-pdf.json"

echo "[Startup] ========================================"
echo "[Startup] MinerU API Startup"
echo "[Startup] ========================================"
echo "[Startup] Models directory: $MODELS_DIR"

# Show disk usage
echo "[Startup] Disk usage:"
df -h /root/cache 2>/dev/null || echo "[Startup] /root/cache not mounted as separate disk"

# Create magic-pdf.json config
cat > "$CONFIG_PATH" << EOF
{
    "device-mode": "cpu",
    "models-dir": "$MODELS_DIR",
    "table-config": {
        "model": "rapid_table",
        "enable": false
    },
    "formula-config": {
        "model": "unimernet_small",
        "enable": true
    },
    "layout-config": {
        "model": "layoutlmv3"
    }
}
EOF

echo "[Startup] Config written to $CONFIG_PATH"

# Check if models exist, if not download them
KEY_MODEL="$MODELS_DIR/MFD/YOLO/yolo_v8_ft.pt"
if [ -f "$KEY_MODEL" ]; then
    echo "[Startup] MinerU models found - full parsing available"
    ls -la "$MODELS_DIR"
else
    echo "[Startup] MinerU models NOT found - starting download..."
    echo "[Startup] This will take ~10-15 minutes for first deployment..."
    
    # Run the download script
    python /app/download_models.py
    
    # Verify download succeeded
    if [ -f "$KEY_MODEL" ]; then
        echo "[Startup] Models downloaded successfully!"
    else
        echo "[Startup] WARNING: Model download may have failed"
        echo "[Startup] Tesseract OCR fallback will be used"
    fi
fi

# Show final disk usage
echo "[Startup] Final disk usage:"
df -h /root/cache 2>/dev/null || true
du -sh /root/cache/* 2>/dev/null || true

# Start the API
echo "[Startup] Starting uvicorn on port $PORT..."
exec uvicorn api:app --host 0.0.0.0 --port "$PORT"
