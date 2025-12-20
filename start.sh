#!/bin/bash
# MinerU API startup script
# Downloads models if missing, creates config, and starts uvicorn

set -e

MODELS_DIR="${MINERU_MODELS_DIR:-/root/.cache/models}"
CONFIG_PATH="/root/magic-pdf.json"

echo "[Startup] ========================================"
echo "[Startup] MinerU API Startup"
echo "[Startup] ========================================"
echo "[Startup] Models directory: $MODELS_DIR"

# Show disk usage
echo "[Startup] Disk usage:"
df -h /root/.cache 2>/dev/null || echo "[Startup] /root/.cache not mounted as separate disk"

# Create magic-pdf.json config
# Note: formula-config.enable is false because the model names in the HF repo
# don't match what magic-pdf expects (unimernet_hf_small_2503 vs unimernet_small)
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
        "enable": false
    },
    "layout-config": {
        "model": "layoutlmv3"
    }
}
EOF

echo "[Startup] Config written to $CONFIG_PATH"
cat "$CONFIG_PATH"

# Check if models exist by looking for Layout directory (most reliable indicator)
# Different model repos may have different structures, so check for common patterns
models_found=false

if [ -d "$MODELS_DIR/Layout" ] || [ -d "$MODELS_DIR/MFD" ]; then
    models_found=true
fi

if [ "$models_found" = true ]; then
    echo "[Startup] MinerU models found - full parsing available"
    echo "[Startup] Models structure:"
    ls -la "$MODELS_DIR" 2>/dev/null || true
    # Show subdirectory structure
    for dir in "$MODELS_DIR"/*/; do
        if [ -d "$dir" ]; then
            echo "[Startup]   $(basename "$dir")/"
            ls "$dir" 2>/dev/null | head -5 | sed 's/^/[Startup]     /'
        fi
    done
else
    echo "[Startup] MinerU models NOT found - starting download..."
    echo "[Startup] This will take ~10-15 minutes for first deployment..."
    
    # Run the download script
    python /app/download_models.py
    
    # Check again after download
    if [ -d "$MODELS_DIR/Layout" ] || [ -d "$MODELS_DIR/MFD" ]; then
        echo "[Startup] Models downloaded successfully!"
        echo "[Startup] Models structure:"
        ls -la "$MODELS_DIR" 2>/dev/null || true
    else
        echo "[Startup] WARNING: Model download may have failed"
        echo "[Startup] Tesseract OCR fallback will be used"
        echo "[Startup] Contents of $MODELS_DIR:"
        ls -la "$MODELS_DIR" 2>/dev/null || echo "[Startup] Directory does not exist"
    fi
fi

# Show final disk usage
echo "[Startup] Final disk usage:"
df -h /root/.cache 2>/dev/null || true
du -sh /root/.cache/* 2>/dev/null || true

# Start the API
echo "[Startup] Starting uvicorn on port $PORT..."
exec uvicorn api:app --host 0.0.0.0 --port "$PORT"
