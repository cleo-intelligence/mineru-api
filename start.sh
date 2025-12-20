#!/bin/bash
# MinerU API startup script
# Creates config and starts uvicorn

set -e

MODELS_DIR="${MINERU_MODELS_DIR:-/data/models}"
CONFIG_PATH="/root/magic-pdf.json"

echo "[Startup] Checking models directory: $MODELS_DIR"

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

# Check if models exist
if [ -d "$MODELS_DIR/MFD" ] && [ -d "$MODELS_DIR/Layout" ]; then
    echo "[Startup] MinerU models found - full parsing available"
else
    echo "[Startup] MinerU models NOT found - Tesseract fallback will be used"
    echo "[Startup] To enable full MinerU, run: python /app/download_models.py"
fi

# Start the API
echo "[Startup] Starting uvicorn on port $PORT..."
exec uvicorn api:app --host 0.0.0.0 --port "$PORT"
