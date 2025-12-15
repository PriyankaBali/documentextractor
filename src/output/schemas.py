"""Pydantic schemas for API request/response and data validation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Processing status of a document."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class DocumentTypeEnum(str, Enum):
    """Supported document types."""
    TRANSCRIPT = "transcript"
    ID_DOCUMENT = "id_document"
    CERTIFICATE = "certificate"
    UNKNOWN = "unknown"


# ============== Request Schemas ==============

class ExtractionRequest(BaseModel):
    """Request to extract data from uploaded documents."""
    
    document_type: DocumentTypeEnum | None = Field(
        default=None,
        description="Optional hint for document type. If not provided, auto-detection is used."
    )
    

class BatchExtractionRequest(BaseModel):
    """Request for batch document processing."""
    
    callback_url: str | None = Field(
        default=None,
        description="URL to POST results when processing completes"
    )


# ============== Response Schemas ==============

class ExtractedFieldResponse(BaseModel):
    """A single extracted field."""
    
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str | None = None


class ExtractionError(BaseModel):
    """Error information for extraction issues."""
    
    code: str
    field: str | None = None
    message: str
    suggested_action: str | None = None


class ExtractionResponse(BaseModel):
    """Response containing extracted document data."""
    
    document_id: str
    status: DocumentStatus
    document_type: DocumentTypeEnum
    filename: str
    
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    field_confidences: dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    
    errors: list[ExtractionError] = Field(default_factory=list)
    requires_review: bool = False
    
    processing_time_ms: int | None = None
    model_used: str | None = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_abc123",
                "status": "completed",
                "document_type": "transcript",
                "filename": "transcript.pdf",
                "extracted_data": {
                    "student_name": "John Smith",
                    "institution_name": "State University",
                    "gpa": 3.75,
                    "graduation_date": "2024-05-15"
                },
                "field_confidences": {
                    "student_name": 0.95,
                    "institution_name": 0.92,
                    "gpa": 0.88,
                    "graduation_date": 0.85
                },
                "overall_confidence": 0.90,
                "errors": [],
                "requires_review": False,
                "processing_time_ms": 2340,
                "model_used": "ollama/llama3.2"
            }
        }


class BatchExtractionResponse(BaseModel):
    """Response for batch processing request."""
    
    batch_id: str
    total_documents: int
    status: str = "processing"
    results: list[ExtractionResponse] = Field(default_factory=list)
    

class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "healthy"
    version: str
    ollama_available: bool = False
    database_connected: bool = False


# ============== Database Schemas (for PostgreSQL JSONB) ==============

class DocumentRecord(BaseModel):
    """Database record for processed documents."""
    
    id: str
    filename: str
    file_size: int
    document_type: DocumentTypeEnum
    status: DocumentStatus
    
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    confidences: dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    
    ocr_text: str | None = None
    raw_llm_response: str | None = None
    
    errors: list[dict] = Field(default_factory=list)
    requires_review: bool = False
    
    processing_time_ms: int | None = None
    model_used: str | None = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== Form Field Mapping ==============

class FormFieldMapping(BaseModel):
    """Mapping of extracted fields to form fields."""
    
    source_field: str
    target_field: str
    transform: str | None = None  # Optional transformation rule


class FormMappingConfig(BaseModel):
    """Configuration for mapping extracted data to a form."""
    
    form_name: str
    document_type: DocumentTypeEnum
    mappings: list[FormFieldMapping]
