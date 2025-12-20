"""
MinerU API - FastAPI wrapper for magic-pdf
Endpoints:
  - POST /file_parse - Parse PDF to Markdown (legacy, multi-file)
  - POST /api/parse - Parse single PDF with OCR support
"""
import os
import subprocess
import tempfile
import time
import traceback
from typing import List, Optional, Literal

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="MinerU API",
    description="Document parsing API using MinerU/magic-pdf with Tesseract fallback",
    version="1.3.1"
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
    return {"status": "healthy", "version": "1.3.1"}


def tesseract_ocr_fallback(pdf_path: str, lang: Optional[str] = None) -> tuple[str, dict]:
    """
    Fallback OCR using Tesseract when MinerU models are not available.
    Uses poppler (pdftoppm) to convert PDF to images, then Tesseract for OCR.
    
    Args:
        pdf_path: Path to the PDF file
        lang: Language code (fra, eng, etc.)
    
    Returns:
        Tuple of (markdown_content, metadata)
    """
    # Use French + English by default
    tesseract_lang = lang if lang else "fra+eng"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Convert PDF to images using pdftoppm (from poppler-utils)
        print(f"[tesseract_fallback] Converting PDF to images...")
        print(f"[tesseract_fallback] PDF path: {pdf_path}, size: {os.path.getsize(pdf_path)} bytes")
        image_prefix = os.path.join(tmp_dir, "page")
        
        try:
            result = subprocess.run(
                ["pdftoppm", "-png", "-r", "300", pdf_path, image_prefix],
                capture_output=True,
                timeout=120
            )
            print(f"[tesseract_fallback] pdftoppm stdout: {result.stdout.decode()[:500]}")
            print(f"[tesseract_fallback] pdftoppm stderr: {result.stderr.decode()[:500]}")
            if result.returncode != 0:
                raise Exception(f"pdftoppm failed with code {result.returncode}: {result.stderr.decode()}")
        except subprocess.TimeoutExpired:
            raise Exception("PDF to image conversion timed out")
        
        # Find generated images
        all_files = os.listdir(tmp_dir)
        print(f"[tesseract_fallback] Files in tmp_dir: {all_files}")
        
        images = sorted([
            os.path.join(tmp_dir, f) 
            for f in all_files 
            if f.startswith("page") and f.endswith(".png")
        ])
        
        if not images:
            # Try without prefix filter
            images = sorted([
                os.path.join(tmp_dir, f) 
                for f in all_files 
                if f.endswith(".png")
            ])
            print(f"[tesseract_fallback] Found {len(images)} PNG files without prefix filter")
        
        if not images:
            raise Exception(f"No images generated from PDF. Files in dir: {all_files}")
        
        # Log image sizes
        for img in images:
            img_size = os.path.getsize(img)
            print(f"[tesseract_fallback] Image: {os.path.basename(img)}, size: {img_size} bytes")
        
        print(f"[tesseract_fallback] Generated {len(images)} page images, running OCR with lang={tesseract_lang}...")
        
        # Run Tesseract on each image
        all_text = []
        for i, image_path in enumerate(images):
            try:
                result = subprocess.run(
                    ["tesseract", image_path, "stdout", "-l", tesseract_lang],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                page_text = result.stdout.strip()
                stderr = result.stderr.strip()
                
                print(f"[tesseract_fallback] Page {i + 1}: {len(page_text)} chars, returncode={result.returncode}")
                if stderr:
                    print(f"[tesseract_fallback] Page {i + 1} stderr: {stderr[:300]}")
                if not page_text and result.returncode == 0:
                    print(f"[tesseract_fallback] Page {i + 1}: Empty output but success - image may be blank or unreadable")
                
                if page_text:
                    all_text.append(f"## Page {i + 1}\n\n{page_text}")
                else:
                    all_text.append(f"## Page {i + 1}\n\n[Page vide ou illisible]")
                    
            except subprocess.TimeoutExpired:
                print(f"[tesseract_fallback] Page {i + 1} OCR timed out")
                all_text.append(f"## Page {i + 1}\n\n[OCR timeout]")
            except Exception as e:
                print(f"[tesseract_fallback] Page {i + 1} OCR error: {e}")
                all_text.append(f"## Page {i + 1}\n\n[OCR error: {e}]")
        
        markdown = "\n\n".join(all_text)
        metadata = {
            "parse_method": "tesseract_fallback",
            "ocr_applied": True,
            "pages": len(images),
            "lang": tesseract_lang,
        }
        
        print(f"[tesseract_fallback] Total: {len(markdown)} chars from {len(images)} pages")
        return markdown, metadata


@app.post("/api/parse", response_model=ParseResponse)
async def api_parse(
    file: UploadFile = File(...),
    parse_method: Literal["auto", "ocr", "txt"] = Form(default="auto"),
    lang: Optional[str] = Form(default=None),
):
    """
    Parse a single PDF to Markdown with OCR support.
    
    Uses MinerU/magic-pdf for advanced parsing. Falls back to Tesseract OCR
    if MinerU models are not available (common in lightweight deployments).
    
    Args:
        file: The PDF file to parse
        parse_method: Parsing method - 'auto' (detect), 'ocr' (force OCR), 'txt' (text only)
        lang: Language hint (fra, eng, etc.)
    
    Returns:
        ParseResponse with markdown content and metadata
    """
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
        
        print(f"[api_parse] Saved file to {tmp_path}, size: {len(content)} bytes")
        
        # Try MinerU first
        try:
            from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
            from magic_pdf.data.dataset import PymuDocDataset
            from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
            
            with tempfile.TemporaryDirectory() as output_dir:
                reader = FileBasedDataReader("")
                writer = FileBasedDataWriter(output_dir)
                
                print(f"[api_parse] Reading PDF bytes...")
                pdf_bytes = reader.read(tmp_path)
                print(f"[api_parse] Creating dataset...")
                dataset = PymuDocDataset(pdf_bytes)
                
                use_ocr = parse_method != "txt"
                
                print(f"[api_parse] Running doc_analyze with ocr={use_ocr}...")
                model_json = doc_analyze(
                    dataset,
                    ocr=use_ocr,
                    show_log=False
                )
                print(f"[api_parse] doc_analyze completed")
                
                print(f"[api_parse] Applying model to dataset...")
                pipe_result = dataset.apply(
                    model_json,
                    imageWriter=writer
                )
                print(f"[api_parse] Getting markdown...")
                md_content = pipe_result.get_markdown()
                print(f"[api_parse] Markdown length: {len(md_content)} chars")
                
                processing_time = int((time.time() - start_time) * 1000)
                
                metadata = {
                    "parse_method": parse_method,
                    "ocr_applied": use_ocr,
                    "pages": len(dataset),
                    "processing_time_ms": processing_time,
                    "lang": lang,
                }
                
                return ParseResponse(content=md_content, metadata=metadata)
        
        except FileNotFoundError as e:
            # MinerU models not available - fall back to Tesseract
            print(f"[api_parse] MinerU models not available: {e}")
            print(f"[api_parse] Falling back to Tesseract OCR...")
            
            md_content, metadata = tesseract_ocr_fallback(tmp_path, lang)
            processing_time = int((time.time() - start_time) * 1000)
            metadata["processing_time_ms"] = processing_time
            
            return ParseResponse(content=md_content, metadata=metadata)
        
        except ImportError as e:
            # MinerU not installed - fall back to Tesseract
            print(f"[api_parse] MinerU not installed: {e}")
            print(f"[api_parse] Falling back to Tesseract OCR...")
            
            md_content, metadata = tesseract_ocr_fallback(tmp_path, lang)
            processing_time = int((time.time() - start_time) * 1000)
            metadata["processing_time_ms"] = processing_time
            
            return ParseResponse(content=md_content, metadata=metadata)
        
    except Exception as e:
        print(f"[api_parse] ERROR: {type(e).__name__}: {str(e)}")
        print(f"[api_parse] Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
    
    finally:
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
            print(f"[file_parse] ERROR for {file.filename}: {type(e).__name__}: {str(e)}")
            results.append({
                "filename": file.filename,
                "error": f"{type(e).__name__}: {str(e)}"
            })
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    return JSONResponse(content=results)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
