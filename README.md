# MinerU API

FastAPI wrapper for MinerU/magic-pdf document parsing with Tesseract OCR fallback.

## Features

- **Full MinerU parsing** - Advanced PDF parsing with layout analysis, table detection, and formula recognition
- **Tesseract fallback** - Automatic fallback to Tesseract OCR when MinerU models are unavailable
- **French + English OCR** - Pre-installed language packs for fra+eng

## Endpoints

- `GET /health` - Health check
- `POST /api/parse` - Parse single PDF to Markdown
- `POST /file_parse` - Parse multiple files (legacy)

## Deployment on Render

### Quick Start (Tesseract only)

1. Create a new Web Service from this repo
2. Deploy - Tesseract fallback works immediately

### Full MinerU (with persistent disk)

1. Create a new Web Service from this repo
2. Add a **Disk** in Render settings:
   - Name: `models`
   - Mount Path: `/data`
   - Size: 10 GB (~$2.50/month)
3. After first deployment, SSH into the service and run:
   ```bash
   python /app/download_models.py
   ```
4. Restart the service

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Server port (set by Render) |
| `MINERU_MODELS_DIR` | `/data/models` | Path to MinerU models |

## API Usage

### Parse a PDF

```bash
curl -X POST \
  -F "file=@document.pdf" \
  -F "parse_method=ocr" \
  -F "lang=fra" \
  https://your-service.onrender.com/api/parse
```

### Response

```json
{
  "content": "# Document Title\n\nExtracted markdown content...",
  "metadata": {
    "parse_method": "ocr",
    "ocr_applied": true,
    "pages": 5,
    "processing_time_ms": 12345
  }
}
```

## Parse Methods

- `auto` - Detect if OCR is needed (default)
- `ocr` - Force OCR processing (for scanned PDFs)
- `txt` - Text extraction only (no OCR)

## Model Download

To manually download MinerU models:

```bash
# SSH into your Render service
python /app/download_models.py

# Force re-download
python /app/download_models.py --force
```

Models are downloaded from [wanderkid/PDF-Extract-Kit](https://huggingface.co/wanderkid/PDF-Extract-Kit) on Hugging Face.
