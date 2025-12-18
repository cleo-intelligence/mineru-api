"""
MinerU API - FastAPI wrapper for magic-pdf
Endpoint: POST /file_parse - Parse PDF to Markdown
"""
import os
import tempfile
import time
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(
    title="MinerU API",
    description="Document parsing API using MinerU/magic-pdf",
    version="1.0.0"
)


@app.get("/docs")
async def docs_redirect():
    """Health check endpoint (redirects to Swagger UI)"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/file_parse")
async def file_parse(files: List[UploadFile] = File(...)):
    """
    Parse PDF/image files to Markdown using MinerU.
    
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
                
                # Analyze document
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
                        "tables_detected": md_content.count("|"),  # Rough estimate
                        "formulas_detected": md_content.count("$")  # Rough estimate
                    }
                })
            
            # Cleanup temp file
            os.unlink(tmp_path)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return JSONResponse(content=results)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
