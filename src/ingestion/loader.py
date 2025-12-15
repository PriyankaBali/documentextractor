"""Document loader with file type detection and validation."""

import mimetypes
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import BinaryIO

from PIL import Image


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
    UNKNOWN = "unknown"


@dataclass
class LoadedDocument:
    """Represents a loaded document ready for processing."""
    
    file_path: Path
    document_type: DocumentType
    file_size: int
    content: bytes
    images: list[Image.Image] = field(default_factory=list)
    text_content: str = ""
    metadata: dict = field(default_factory=dict)


MIME_TYPE_MAP = {
    "application/pdf": DocumentType.PDF,
    "image/jpeg": DocumentType.IMAGE,
    "image/png": DocumentType.IMAGE,
    "image/tiff": DocumentType.IMAGE,
    "image/webp": DocumentType.IMAGE,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
}

EXTENSION_MAP = {
    ".pdf": DocumentType.PDF,
    ".jpg": DocumentType.IMAGE,
    ".jpeg": DocumentType.IMAGE,
    ".png": DocumentType.IMAGE,
    ".tiff": DocumentType.IMAGE,
    ".tif": DocumentType.IMAGE,
    ".webp": DocumentType.IMAGE,
    ".docx": DocumentType.DOCX,
}


class DocumentValidationError(Exception):
    """Raised when document validation fails."""
    pass


class DocumentLoader:
    """Load and validate documents for processing."""
    
    def __init__(self, max_file_size_bytes: int = 50 * 1024 * 1024):
        """Initialize loader with size limit.
        
        Args:
            max_file_size_bytes: Maximum allowed file size in bytes.
        """
        self.max_file_size_bytes = max_file_size_bytes
    
    def detect_type(self, file_path: Path, content: bytes | None = None) -> DocumentType:
        """Detect document type from file extension and MIME type.
        
        Args:
            file_path: Path to the file.
            content: Optional file content for magic byte detection.
            
        Returns:
            Detected DocumentType.
        """
        # Try extension first
        ext = file_path.suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]
        
        # Try MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type in MIME_TYPE_MAP:
            return MIME_TYPE_MAP[mime_type]
        
        # Try magic bytes if content provided
        if content:
            if content[:4] == b"%PDF":
                return DocumentType.PDF
            if content[:8] == b"\x89PNG\r\n\x1a\n":
                return DocumentType.IMAGE
            if content[:2] == b"\xff\xd8":  # JPEG
                return DocumentType.IMAGE
            if content[:4] == b"PK\x03\x04":  # ZIP (DOCX)
                return DocumentType.DOCX
        
        return DocumentType.UNKNOWN
    
    def validate(self, file_path: Path, content: bytes) -> None:
        """Validate document before processing.
        
        Args:
            file_path: Path to the file.
            content: File content bytes.
            
        Raises:
            DocumentValidationError: If validation fails.
        """
        # Check file size
        if len(content) > self.max_file_size_bytes:
            raise DocumentValidationError(
                f"File size {len(content)} bytes exceeds maximum "
                f"{self.max_file_size_bytes} bytes"
            )
        
        # Check if empty
        if len(content) == 0:
            raise DocumentValidationError("File is empty")
        
        # Check document type
        doc_type = self.detect_type(file_path, content)
        if doc_type == DocumentType.UNKNOWN:
            raise DocumentValidationError(
                f"Unsupported file type: {file_path.suffix}. "
                "Supported types: PDF, JPG, PNG, DOCX"
            )
    
    def load_from_path(self, file_path: Path) -> LoadedDocument:
        """Load document from file path.
        
        Args:
            file_path: Path to the document.
            
        Returns:
            LoadedDocument instance.
            
        Raises:
            DocumentValidationError: If file doesn't exist or validation fails.
        """
        if not file_path.exists():
            raise DocumentValidationError(f"File not found: {file_path}")
        
        content = file_path.read_bytes()
        self.validate(file_path, content)
        
        doc_type = self.detect_type(file_path, content)
        
        return LoadedDocument(
            file_path=file_path,
            document_type=doc_type,
            file_size=len(content),
            content=content,
            metadata={"filename": file_path.name},
        )
    
    def load_from_bytes(
        self, 
        content: bytes, 
        filename: str,
    ) -> LoadedDocument:
        """Load document from bytes (for file uploads).
        
        Args:
            content: File content as bytes.
            filename: Original filename.
            
        Returns:
            LoadedDocument instance.
        """
        file_path = Path(filename)
        self.validate(file_path, content)
        
        doc_type = self.detect_type(file_path, content)
        
        return LoadedDocument(
            file_path=file_path,
            document_type=doc_type,
            file_size=len(content),
            content=content,
            metadata={"filename": filename},
        )
    
    async def load_from_upload(
        self,
        file: BinaryIO,
        filename: str,
    ) -> LoadedDocument:
        """Load document from file upload (async-friendly).
        
        Args:
            file: File-like object.
            filename: Original filename.
            
        Returns:
            LoadedDocument instance.
        """
        content = file.read()
        return self.load_from_bytes(content, filename)
