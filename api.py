"""
MinerU API - FastAPI wrapper for magic-pdf
Endpoints:
  - POST /file_parse - Parse PDF to Markdown (legacy, multi-file)
  - POST /api/parse - Parse single PDF with OCR support
"""
import os
import tempfile
import time
from typing import List, Optional, Literal

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="MinerU API",
    description="Document parsing API using MinerU/magic-pdf",
    version="1.2.0"
)


class ParseResponse(BaseModel):
    content: str
    metadata: Optional[dict] = None


@app.get("/docs")
async def docs_redirect():
    """Health check endpoint (redirects to Swagger UI)"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.2.0"}


@app.post("/api/parse", response_model=ParseResponse)
async def api_parse(
    file: UploadFile = File(...),
    parse_method: Literal["auto", "ocr", "txt"] = Form(default="auto"),
    lang: Optional[str] = Form(default=None),
):
    """
    Parse a single PDF to Markdown with OCR support.
    
    Args:
        file: The PDF file to parse
        parse_method: Parsing method - 'auto' (detect), 'ocr' (force OCR), 'txt' (text only)
        lang: Language hint (stored in metadata, not used by parser)
    
    Returns:
        ParseResponse with markdown content and metadata
    """
    try:
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
        from magic_pdf.data.dataset import PymuDocDataset
        from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MinerU not properly installed: {str(e)}"
        )
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    
    start_time = time.time()
    tmp_path = None
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Create output directory
        with tempfile.TemporaryDirectory() as output_dir:
            # Initialize MinerU components
            reader = FileBasedDataReader("")
            writer = FileBasedDataWriter(output_dir)
            
            # Read and process document
            pdf_bytes = reader.read(tmp_path)
            dataset = PymuDocDataset(pdf_bytes)
            
            # Determine OCR setting based on parse_method
            # Always enable OCR for auto and ocr modes (needed for scanned PDFs)
            use_ocr = parse_method != "txt"
            
            # Analyze document
            # Note: doc_analyze does NOT accept a lang parameter
            model_json = doc_analyze(
                dataset,
                ocr=use_ocr,
                show_log=False
            )
            
            # Convert to markdown
            pipe_result = dataset.apply(
                model_json,
                imageWriter=writer
            )
            
            md_content = pipe_result.get_markdown()
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Build metadata
            metadata = {
                "parse_method": parse_method,
                "ocr_applied": use_ocr,
                "pages": len(dataset),
                "processing_time_ms": processing_time,
                "lang": lang,  # Stored for reference
            }
            
            return ParseResponse(content=md_content, metadata=metadata)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/file_parse")
async def file_parse(files: List[UploadFile] = File(...)):
    """
    Parse PDF/image files to Markdown using MinerU (legacy multi-file endpoint).
    
    Args:
        files: List of files to parse (PDF or images)
    
    Returns:
        List of parsing results with markdown content
    """
    try:
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
        from magic_pdf.data.dataset import PymuDocDataset
        from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MinerU not properly installed: {str(e)}"
        )
    
    results = []
    
    for file in files:
        start_time = time.time()
        tmp_path = None
        
        # Validate file type
        if not file.filename:
            continue
            
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            results.append({
                "filename": file.filename,
                "error": f"Unsupported file type: {ext}"
            })
            continue
        
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
            
            # Create output directory
            with tempfile.TemporaryDirectory() as output_dir:
                # Initialize MinerU components
                reader = FileBasedDataReader("")
                writer = FileBasedDataWriter(output_dir)
                
                # Read and process document
                pdf_bytes = reader.read(tmp_path)
                dataset = PymuDocDataset(pdf_bytes)
                
                # Analyze document with OCR enabled
                model_json = doc_analyze(
                    dataset,
                    ocr=True,
                    show_log=False
                )
                
                # Convert to markdown
                pipe_result = dataset.apply(
                    model_json,
                    imageWriter=writer
                )
                
                md_content = pipe_result.get_markdown()
                
                processing_time = int((time.time() - start_time) * 1000)
                
                results.append({
                    "filename": file.filename,
                    "result": {
                        "md": md_content,
                        "pages": len(dataset),
                        "processing_time_ms": processing_time,
                        "ocr_applied": True,
                        "tables_detected": md_content.count("|"),
                        "formulas_detected": md_content.count("$")
                    }
                })
            
            # Cleanup temp file
            if tmp_path:
                os.unlink(tmp_path)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    return JSONResponse(content=results)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
