"""Core document processing pipeline."""

import time
from dataclasses import dataclass
from uuid import uuid4

from PIL import Image

from .ingestion.loader import DocumentLoader, DocumentType, LoadedDocument
from .ingestion.pdf_parser import PDFParser
from .ingestion.image_parser import ImageParser
from .ingestion.docx_parser import DocxParser
from .preprocessing.enhancer import ImageEnhancer
from .extraction.ocr_engine import OCRPipeline, OCRResult
from .extraction.llm_extractor import LLMPipeline, ExtractionResult
from .templates.base_template import BaseTemplate, DocumentCategory, TemplateResult
from .templates.transcript import TranscriptTemplate
from .templates.id_document import IDDocumentTemplate
from .templates.certificate import CertificateTemplate
from .templates.indian_ids import (
    AadhaarCardTemplate,
    PANCardTemplate,
    UANCardTemplate,
    VoterIDTemplate,
    DrivingLicenseTemplate,
)
from .output.schemas import (
    ExtractionResponse, 
    DocumentStatus, 
    DocumentTypeEnum,
    ExtractionError,
)
from .config import get_settings


@dataclass
class ProcessingResult:
    """Complete result from document processing."""
    
    document_id: str
    success: bool
    response: ExtractionResponse
    ocr_text: str = ""
    raw_llm_response: str = ""
    processing_time_ms: int = 0


class DocumentProcessor:
    """Main document processing pipeline."""
    
    def __init__(self):
        """Initialize processor with all components."""
        settings = get_settings()
        
        # Initialize components
        self.loader = DocumentLoader(max_file_size_bytes=settings.max_file_size_bytes)
        self.pdf_parser = PDFParser()
        self.image_parser = ImageParser()
        self.docx_parser = DocxParser()
        self.enhancer = ImageEnhancer()
        self.ocr_pipeline = OCRPipeline(
            confidence_threshold=settings.confidence_threshold
        )
        self.llm_pipeline = LLMPipeline(
            confidence_threshold=settings.confidence_threshold
        )
        
        # Document templates (Indian IDs first for better classification)
        self.templates: list[BaseTemplate] = [
            # Indian ID documents
            UANCardTemplate(),
            AadhaarCardTemplate(),
            PANCardTemplate(),
            VoterIDTemplate(),
            DrivingLicenseTemplate(),
            # General templates
            TranscriptTemplate(),
            IDDocumentTemplate(),
            CertificateTemplate(),
        ]
        
        self.confidence_threshold = settings.confidence_threshold
    
    def process_file(
        self, 
        file_path: str | None = None,
        content: bytes | None = None,
        filename: str = "document",
        document_type_hint: DocumentTypeEnum | None = None,
    ) -> ProcessingResult:
        """Process a single document file.
        
        Args:
            file_path: Path to file on disk.
            content: File content as bytes.
            filename: Original filename.
            document_type_hint: Optional hint for document type.
            
        Returns:
            ProcessingResult with extraction data.
        """
        start_time = time.time()
        document_id = str(uuid4())
        
        try:
            # Load document
            if file_path:
                from pathlib import Path
                document = self.loader.load_from_path(Path(file_path))
            elif content:
                document = self.loader.load_from_bytes(content, filename)
            else:
                raise ValueError("Either file_path or content must be provided")
            
            # Extract text based on document type
            text, images = self._extract_content(document)
            
            # Run OCR on images if needed
            ocr_result = None
            if images and (not text or len(text.strip()) < 100):
                ocr_result = self._run_ocr(images)
                text = ocr_result.full_text if ocr_result else text
            
            # Classify document type
            template = self._classify_document(text, document_type_hint)
            
            # Extract fields using LLM
            llm_result = self.llm_pipeline.extract(
                text=text,
                document_type=template.category.value,
                expected_fields=template.field_names,
            )
            
            # Build response
            response = self._build_response(
                document_id=document_id,
                filename=filename,
                template=template,
                llm_result=llm_result,
                ocr_result=ocr_result,
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            response.processing_time_ms = processing_time
            
            return ProcessingResult(
                document_id=document_id,
                success=True,
                response=response,
                ocr_text=text,
                raw_llm_response=llm_result.raw_response,
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            
            response = ExtractionResponse(
                document_id=document_id,
                status=DocumentStatus.FAILED,
                document_type=DocumentTypeEnum.UNKNOWN,
                filename=filename,
                overall_confidence=0.0,
                errors=[ExtractionError(
                    code="PROCESSING_ERROR",
                    message=str(e),
                    suggested_action="Check file format and try again",
                )],
                processing_time_ms=processing_time,
            )
            
            return ProcessingResult(
                document_id=document_id,
                success=False,
                response=response,
                processing_time_ms=processing_time,
            )
    
    def _extract_content(
        self, 
        document: LoadedDocument
    ) -> tuple[str, list[Image.Image]]:
        """Extract text and images from document.
        
        Returns:
            Tuple of (text, list of images).
        """
        text = ""
        images = []
        
        if document.document_type == DocumentType.PDF:
            pages = self.pdf_parser.parse(document)
            text = "\n\n".join(p.text for p in pages)
            images = [p.image for p in pages]
            
        elif document.document_type == DocumentType.IMAGE:
            img_info = self.image_parser.parse(document)
            images = [img_info.image]
            
        elif document.document_type == DocumentType.DOCX:
            docx_content = self.docx_parser.parse(document)
            text = docx_content.full_text
        
        return text, images
    
    def _run_ocr(self, images: list[Image.Image]) -> OCRResult | None:
        """Run OCR on images.
        
        Returns:
            Combined OCR result.
        """
        if not images:
            return None
        
        all_text = []
        total_confidence = 0
        
        for image in images:
            # Enhance image first
            enhanced = self.enhancer.enhance(image)
            
            # Run OCR
            result = self.ocr_pipeline.process(enhanced)
            all_text.append(result.full_text)
            total_confidence += result.confidence
        
        from .extraction.ocr_engine import OCRResult
        return OCRResult(
            full_text="\n\n".join(all_text),
            words=[],
            confidence=total_confidence / len(images) if images else 0,
            engine_used="pipeline",
        )
    
    def _classify_document(
        self,
        text: str,
        type_hint: DocumentTypeEnum | None = None,
    ) -> BaseTemplate:
        """Classify document and return appropriate template.
        
        Args:
            text: Document text.
            type_hint: Optional hint for document type.
            
        Returns:
            Best matching template.
        """
        # If hint provided, use corresponding template
        if type_hint:
            for template in self.templates:
                if template.category.value == type_hint.value:
                    return template
        
        # Otherwise, classify based on content
        best_template = self.templates[0]
        best_score = 0
        
        for template in self.templates:
            score = template.classify(text)
            if score > best_score:
                best_score = score
                best_template = template
        
        return best_template
    
    def _build_response(
        self,
        document_id: str,
        filename: str,
        template: BaseTemplate,
        llm_result: ExtractionResult,
        ocr_result: OCRResult | None,
    ) -> ExtractionResponse:
        """Build extraction response from results.
        
        Args:
            document_id: Unique document ID.
            filename: Original filename.
            template: Document template used.
            llm_result: LLM extraction result.
            ocr_result: OCR result if applicable.
            
        Returns:
            Complete ExtractionResponse.
        """
        # Extract field values and confidences
        extracted_data = {}
        field_confidences = {}
        
        for field_name, field in llm_result.fields.items():
            extracted_data[field_name] = field.value
            field_confidences[field_name] = field.confidence
        
        # Post-process fields
        extracted_data = template.post_process(extracted_data)
        
        # Validate fields
        validation_errors = template.validate(extracted_data)
        
        # Calculate overall confidence (only count fields with non-null values)
        non_null_confidences = [
            conf for field_name, conf in field_confidences.items()
            if extracted_data.get(field_name) is not None
        ]
        if non_null_confidences:
            overall_confidence = sum(non_null_confidences) / len(non_null_confidences)
        else:
            overall_confidence = 0.0
        
        # Adjust for OCR confidence if applicable
        if ocr_result and ocr_result.confidence < 0.7:
            overall_confidence *= ocr_result.confidence
        
        # Determine status
        errors = []
        requires_review = False
        
        if not llm_result.success:
            status = DocumentStatus.FAILED
            errors.append(ExtractionError(
                code="LLM_ERROR",
                message=llm_result.error,
                suggested_action="Try again or use different model",
            ))
        elif validation_errors:
            status = DocumentStatus.REQUIRES_REVIEW
            requires_review = True
            for err in validation_errors:
                errors.append(ExtractionError(
                    code="VALIDATION_ERROR",
                    message=err,
                    suggested_action="Manual review required",
                ))
        elif overall_confidence < self.confidence_threshold:
            status = DocumentStatus.REQUIRES_REVIEW
            requires_review = True
            errors.append(ExtractionError(
                code="LOW_CONFIDENCE",
                message=f"Overall confidence {overall_confidence:.2f} below threshold",
                suggested_action="Manual verification recommended",
            ))
        else:
            status = DocumentStatus.COMPLETED
        
        # Map category to document type enum
        doc_type_map = {
            DocumentCategory.TRANSCRIPT: DocumentTypeEnum.TRANSCRIPT,
            DocumentCategory.ID_DOCUMENT: DocumentTypeEnum.ID_DOCUMENT,
            DocumentCategory.CERTIFICATE: DocumentTypeEnum.CERTIFICATE,
        }
        doc_type = doc_type_map.get(template.category, DocumentTypeEnum.UNKNOWN)
        
        return ExtractionResponse(
            document_id=document_id,
            status=status,
            document_type=doc_type,
            filename=filename,
            extracted_data=extracted_data,
            field_confidences=field_confidences,
            overall_confidence=overall_confidence,
            errors=errors,
            requires_review=requires_review,
            model_used=llm_result.model_used,
        )
