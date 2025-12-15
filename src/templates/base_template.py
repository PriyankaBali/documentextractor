"""Base template class for document extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DocumentCategory(str, Enum):
    """Categories of admission documents."""
    TRANSCRIPT = "transcript"
    ID_DOCUMENT = "id_document"
    CERTIFICATE = "certificate"
    RECOMMENDATION = "recommendation"
    ESSAY = "essay"
    UNKNOWN = "unknown"


@dataclass
class FieldDefinition:
    """Definition of an expected field."""
    
    name: str
    display_name: str
    field_type: str  # string, number, date, array
    required: bool = True
    validation_pattern: str | None = None
    description: str = ""


@dataclass 
class TemplateResult:
    """Result from template-based extraction."""
    
    category: DocumentCategory
    fields: dict[str, Any]
    confidence_scores: dict[str, float]
    overall_confidence: float
    validation_errors: list[str] = field(default_factory=list)
    requires_review: bool = False


class BaseTemplate(ABC):
    """Abstract base class for document templates."""
    
    category: DocumentCategory = DocumentCategory.UNKNOWN
    
    @property
    @abstractmethod
    def field_definitions(self) -> list[FieldDefinition]:
        """Define expected fields for this document type."""
        pass
    
    @property
    def field_names(self) -> list[str]:
        """Get list of field names."""
        return [f.name for f in self.field_definitions]
    
    @property
    def required_fields(self) -> list[str]:
        """Get list of required field names."""
        return [f.name for f in self.field_definitions if f.required]
    
    def classify(self, text: str) -> float:
        """Return confidence that text matches this template.
        
        Args:
            text: Document text to classify.
            
        Returns:
            Confidence score 0.0-1.0.
        """
        # Default implementation using keywords
        text_lower = text.lower()
        matches = sum(1 for kw in self.classification_keywords if kw in text_lower)
        return min(matches / max(len(self.classification_keywords), 1), 1.0)
    
    @property
    def classification_keywords(self) -> list[str]:
        """Keywords that indicate this document type."""
        return []
    
    def validate(self, fields: dict[str, Any]) -> list[str]:
        """Validate extracted fields.
        
        Args:
            fields: Extracted field values.
            
        Returns:
            List of validation error messages.
        """
        errors = []
        
        for field_def in self.field_definitions:
            value = fields.get(field_def.name)
            
            # Check required fields
            if field_def.required and (value is None or value == ""):
                errors.append(f"Required field '{field_def.display_name}' is missing")
            
            # Type validation
            if value is not None and value != "":
                if field_def.field_type == "number":
                    try:
                        float(str(value).replace(",", ""))
                    except ValueError:
                        errors.append(
                            f"Field '{field_def.display_name}' should be a number"
                        )
        
        return errors
    
    def post_process(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Post-process extracted fields.
        
        Args:
            fields: Raw extracted fields.
            
        Returns:
            Processed fields.
        """
        # Default: return as-is
        return fields
