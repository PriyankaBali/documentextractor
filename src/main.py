"""FastAPI application for document extraction."""

import os
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .processor import DocumentProcessor
from .output.schemas import (
    ExtractionResponse,
    BatchExtractionResponse,
    HealthResponse,
    DocumentTypeEnum,
    DocumentStatus,
)

# Initialize FastAPI app
app = FastAPI(
    title="Document Extractor API",
    description="AI-powered document extraction for college admissions",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global processor instance (lazy loaded)
_processor: DocumentProcessor | None = None


def get_processor() -> DocumentProcessor:
    """Get or create document processor."""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    settings = get_settings()
    
    # Create upload directory
    settings.upload_dir.mkdir(parents=True, exist_ok=True)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import ollama
    
    ollama_available = False
    try:
        settings = get_settings()
        client = ollama.Client(host=settings.ollama_host)
        client.list()
        ollama_available = True
    except Exception:
        pass
    
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        ollama_available=ollama_available,
        database_connected=False,  # TODO: Add database check
    )


@app.post("/extract", response_model=ExtractionResponse)
async def extract_document(
    file: UploadFile = File(...),
    document_type: Annotated[
        DocumentTypeEnum | None, 
        Query(description="Optional document type hint")
    ] = None,
):
    """Extract structured data from a single document.
    
    Accepts PDF, JPG, PNG, or DOCX files and returns extracted fields
    with confidence scores.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    settings = get_settings()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )
    
    # Process document
    processor = get_processor()
    result = processor.process_file(
        content=content,
        filename=file.filename,
        document_type_hint=document_type,
    )
    
    return result.response


@app.post("/extract/batch", response_model=BatchExtractionResponse)
async def extract_batch(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
):
    """Extract data from multiple documents.
    
    Processes documents in parallel and returns all results.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 20:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 20 files per batch"
        )
    
    batch_id = str(uuid4())
    processor = get_processor()
    results = []
    
    for file in files:
        if not file.filename:
            continue
            
        content = await file.read()
        if content:
            result = processor.process_file(
                content=content,
                filename=file.filename,
            )
            results.append(result.response)
    
    return BatchExtractionResponse(
        batch_id=batch_id,
        total_documents=len(files),
        status="completed",
        results=results,
    )


@app.post("/extract/url")
async def extract_from_url(
    url: str,
    document_type: DocumentTypeEnum | None = None,
):
    """Extract data from a document at a URL.
    
    Downloads and processes the document from the given URL.
    """
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            content = response.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download: {str(e)}")
    
    # Extract filename from URL
    filename = url.split("/")[-1].split("?")[0] or "document"
    
    processor = get_processor()
    result = processor.process_file(
        content=content,
        filename=filename,
        document_type_hint=document_type,
    )
    
    return result.response


@app.get("/templates")
async def list_templates():
    """List available document templates and their expected fields."""
    processor = get_processor()
    
    templates = []
    for template in processor.templates:
        templates.append({
            "category": template.category.value,
            "fields": [
                {
                    "name": f.name,
                    "display_name": f.display_name,
                    "type": f.field_type,
                    "required": f.required,
                    "description": f.description,
                }
                for f in template.field_definitions
            ],
        })
    
    return {"templates": templates}


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


def main():
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
