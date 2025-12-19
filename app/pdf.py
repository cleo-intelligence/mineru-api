import os
from pathlib import Path
from typing import Optional, Literal
from uuid import uuid4

import magic_pdf.model as model_config
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from magic_pdf.pipe.UNIPipe import UNIPipe
from magic_pdf.pipe.OCRPipe import OCRPipe
from magic_pdf.pipe.TXTPipe import TXTPipe
from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
from pydantic import BaseModel

from .office_converter import OfficeConverter, OfficeExts

parse_router = APIRouter()


class ParseResponse(BaseModel):
    content: str
    metadata: Optional[dict] = None


_tmp_dir = "/tmp/{uuid}"
_local_image_dir = "/tmp/{uuid}/images"
model_config.__use_inside_model__ = True
model_config.__model_mode__ = "full"


@parse_router.post("/parse", response_model=ParseResponse)
async def parse(
    file: UploadFile = File(...),
    parse_method: Literal["auto", "ocr", "txt"] = Form(default="auto"),
    lang: Optional[str] = Form(default=None),
):
    """
    Parse a PDF or Office document to Markdown.

    Args:
        file: The document to parse (PDF, DOCX, XLSX, PPTX)
        parse_method: Parsing method - 'auto' (detect), 'ocr' (force OCR), 'txt' (text only)
        lang: Language hint for OCR (e.g., 'fr', 'en')

    Returns:
        ParseResponse with markdown content
    """
    pdf_bytes = None
    uuid_str = str(uuid4())
    tmp_dir = _tmp_dir.format(uuid=uuid_str)
    local_image_dir = _local_image_dir.format(uuid=uuid_str)
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(local_image_dir, exist_ok=True)

    try:
        # Handle Office documents by converting to PDF first
        if file.filename.endswith(OfficeExts.__args__):
            contents = await file.read()
            input_file: Path = Path(tmp_dir) / file.filename
            input_file.write_bytes(contents)
            output_file: Path = Path(tmp_dir) / (os.path.splitext(file.filename)[0] + ".pdf")
            office_converter = OfficeConverter()
            office_converter.convert(input_file, output_file)
            pdf_bytes = output_file.read_bytes()
        elif file.filename.endswith(".pdf"):
            pdf_bytes = await file.read()
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        image_writer = DiskReaderWriter(local_image_dir)
        jso_useful_key = {"_pdf_type": "", "model_list": []}

        # Select the appropriate pipe based on parse_method
        if parse_method == "ocr":
            # Force OCR mode - essential for scanned documents
            pipe = OCRPipe(pdf_bytes, jso_useful_key, image_writer, is_debug=True)
        elif parse_method == "txt":
            # Force text extraction only - for digital PDFs
            pipe = TXTPipe(pdf_bytes, jso_useful_key, image_writer, is_debug=True)
        else:
            # Auto mode - let UNIPipe detect the best method
            pipe = UNIPipe(pdf_bytes, jso_useful_key, image_writer, is_debug=True)

        # Run the parsing pipeline
        pipe.pipe_classify()
        pipe.pipe_analyze()
        pipe.pipe_parse()
        md_content = pipe.pipe_mk_markdown(local_image_dir, drop_mode="none")

        # Build metadata
        metadata = {
            "parse_method": parse_method,
            "detected_type": jso_useful_key.get("_pdf_type", "unknown"),
        }

        return ParseResponse(content=md_content, metadata=metadata)

    finally:
        # Cleanup temporary files
        import shutil
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
