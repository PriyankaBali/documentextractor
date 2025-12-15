"""LLM-based field extraction using Ollama (primary) and Gemini (fallback)."""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import ollama
import google.generativeai as genai

from ..config import get_settings


@dataclass
class ExtractedField:
    """A single extracted field with confidence."""
    
    name: str
    value: Any
    confidence: float
    source_text: str = ""


@dataclass
class ExtractionResult:
    """Result from LLM extraction."""
    
    document_type: str
    fields: dict[str, ExtractedField]
    raw_response: str = ""
    model_used: str = ""
    success: bool = True
    error: str = ""


# Prompt template for field extraction
EXTRACTION_PROMPT = """You are an expert document analyst specializing in Indian identity documents and official records.
Extract structured information from the following document text.

Document Type: {document_type}
Expected Fields: {field_names}

Document Text:
---
{text}
---

IMPORTANT INSTRUCTIONS:
1. Extract ONLY the values that are clearly present in the document
2. For name fields:
   - Use the EXACT name as written in the document
   - Do NOT split names into first/last unless clearly separated
   - If only one name field is visible, put it in the primary name field (full_name, member_name, etc.)
3. For ID numbers (Aadhaar, PAN, UAN, etc.):
   - Extract the complete number exactly as shown
   - Include any spaces or formatting
4. For dates:
   - Use the format DD/MM/YYYY or as shown in document
5. Set confidence based on clarity:
   - 0.95-1.0: Text is crystal clear
   - 0.80-0.94: Text is readable but slightly unclear
   - 0.60-0.79: Text is partially obscured or ambiguous
   - Below 0.60: Guessing or very unclear
6. If a field is NOT FOUND in the document, set value to null and confidence to 0

Return ONLY valid JSON in this exact format:
{{
  "document_type": "{document_type}",
  "fields": {{
    "field_name": {{
      "value": "extracted value or null",
      "confidence": 0.95
    }}
  }}
}}

Return ONLY the JSON, no explanations or other text.
"""



class LLMExtractor(ABC):
    """Abstract base for LLM extractors."""
    
    @abstractmethod
    def extract(
        self, 
        text: str, 
        document_type: str,
        expected_fields: list[str],
    ) -> ExtractionResult:
        """Extract fields from text using LLM."""
        pass
    
    def _parse_response(self, response: str, document_type: str) -> ExtractionResult:
        """Parse LLM JSON response into ExtractionResult."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return ExtractionResult(
                    document_type=document_type,
                    fields={},
                    raw_response=response,
                    success=False,
                    error="No JSON found in response",
                )
            
            data = json.loads(json_match.group())
            
            fields = {}
            for field_name, field_data in data.get("fields", {}).items():
                if isinstance(field_data, dict):
                    fields[field_name] = ExtractedField(
                        name=field_name,
                        value=field_data.get("value"),
                        confidence=float(field_data.get("confidence", 0.5)),
                        source_text=field_data.get("source_text", ""),
                    )
                else:
                    # Simple value without metadata
                    fields[field_name] = ExtractedField(
                        name=field_name,
                        value=field_data,
                        confidence=0.5,
                    )
            
            return ExtractionResult(
                document_type=data.get("document_type", document_type),
                fields=fields,
                raw_response=response,
                success=True,
            )
            
        except json.JSONDecodeError as e:
            return ExtractionResult(
                document_type=document_type,
                fields={},
                raw_response=response,
                success=False,
                error=f"JSON parse error: {str(e)}",
            )


class OllamaExtractor(LLMExtractor):
    """Ollama-based local LLM extractor."""
    
    def __init__(
        self, 
        model: str = None,
        host: str = None,
    ):
        """Initialize Ollama extractor.
        
        Args:
            model: Ollama model name (default: from settings).
            host: Ollama host URL (default: from settings).
        """
        settings = get_settings()
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_host
        
        # Configure Ollama client
        self.client = ollama.Client(host=self.host)
    
    def extract(
        self,
        text: str,
        document_type: str,
        expected_fields: list[str],
    ) -> ExtractionResult:
        """Extract fields using Ollama.
        
        Args:
            text: Document text to analyze.
            document_type: Type of document (transcript, id, certificate).
            expected_fields: List of field names to extract.
            
        Returns:
            ExtractionResult with extracted fields.
        """
        prompt = EXTRACTION_PROMPT.format(
            document_type=document_type,
            field_names=", ".join(expected_fields),
            text=text[:8000],  # Limit text length for context
        )
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},  # Low temp for consistent output
            )
            
            response_text = response["message"]["content"]
            result = self._parse_response(response_text, document_type)
            result.model_used = f"ollama/{self.model}"
            return result
            
        except Exception as e:
            return ExtractionResult(
                document_type=document_type,
                fields={},
                success=False,
                error=f"Ollama error: {str(e)}",
                model_used=f"ollama/{self.model}",
            )


class GeminiExtractor(LLMExtractor):
    """Google Gemini API extractor for fallback."""
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        """Initialize Gemini extractor.
        
        Args:
            api_key: Gemini API key (default: from settings).
            model: Gemini model name.
        """
        settings = get_settings()
        api_key = api_key or settings.gemini_api_key
        
        if not api_key:
            raise ValueError("Gemini API key not configured")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model
    
    def extract(
        self,
        text: str,
        document_type: str,
        expected_fields: list[str],
    ) -> ExtractionResult:
        """Extract fields using Gemini.
        
        Args:
            text: Document text to analyze.
            document_type: Type of document.
            expected_fields: List of field names to extract.
            
        Returns:
            ExtractionResult with extracted fields.
        """
        prompt = EXTRACTION_PROMPT.format(
            document_type=document_type,
            field_names=", ".join(expected_fields),
            text=text[:30000],  # Gemini has larger context
        )
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )
            
            response_text = response.text
            result = self._parse_response(response_text, document_type)
            result.model_used = f"gemini/{self.model_name}"
            return result
            
        except Exception as e:
            return ExtractionResult(
                document_type=document_type,
                fields={},
                success=False,
                error=f"Gemini error: {str(e)}",
                model_used=f"gemini/{self.model_name}",
            )


class LLMPipeline:
    """LLM extraction pipeline with Ollama primary and Gemini fallback."""
    
    def __init__(
        self,
        primary: LLMExtractor = None,
        fallback: LLMExtractor = None,
        use_fallback_on_low_confidence: bool = True,
        confidence_threshold: float = 0.7,
    ):
        """Initialize LLM pipeline.
        
        Args:
            primary: Primary extractor (default: Ollama).
            fallback: Fallback extractor (default: Gemini).
            use_fallback_on_low_confidence: Whether to try fallback on low confidence.
            confidence_threshold: Minimum average confidence before fallback.
        """
        self.primary = primary
        self.fallback = fallback
        self.use_fallback_on_low_confidence = use_fallback_on_low_confidence
        self.confidence_threshold = confidence_threshold
        
        self._primary_initialized = False
        self._fallback_initialized = False
    
    def _ensure_primary(self):
        """Lazy initialize primary extractor."""
        if not self._primary_initialized:
            if self.primary is None:
                self.primary = OllamaExtractor()
            self._primary_initialized = True
    
    def _ensure_fallback(self):
        """Lazy initialize fallback extractor."""
        if not self._fallback_initialized:
            if self.fallback is None:
                try:
                    self.fallback = GeminiExtractor()
                except ValueError:
                    # No Gemini API key configured
                    self.fallback = None
            self._fallback_initialized = True
    
    def extract(
        self,
        text: str,
        document_type: str,
        expected_fields: list[str],
    ) -> ExtractionResult:
        """Extract fields using LLM pipeline.
        
        Args:
            text: Document text.
            document_type: Type of document.
            expected_fields: Expected field names.
            
        Returns:
            Best ExtractionResult from available engines.
        """
        # Try primary (Ollama)
        self._ensure_primary()
        try:
            result = self.primary.extract(text, document_type, expected_fields)
            
            if result.success:
                # Check confidence
                avg_confidence = self._average_confidence(result)
                
                if avg_confidence >= self.confidence_threshold:
                    return result
                
                # Try fallback if configured
                if self.use_fallback_on_low_confidence:
                    self._ensure_fallback()
                    if self.fallback:
                        fallback_result = self.fallback.extract(
                            text, document_type, expected_fields
                        )
                        if fallback_result.success:
                            fallback_conf = self._average_confidence(fallback_result)
                            if fallback_conf > avg_confidence:
                                return fallback_result
                
                return result
            
            # Primary failed, try fallback
            self._ensure_fallback()
            if self.fallback:
                return self.fallback.extract(text, document_type, expected_fields)
            return result
            
        except Exception as e:
            # Primary raised exception, try fallback
            self._ensure_fallback()
            if self.fallback:
                return self.fallback.extract(text, document_type, expected_fields)
            
            return ExtractionResult(
                document_type=document_type,
                fields={},
                success=False,
                error=f"All extractors failed: {str(e)}",
            )
    
    def _average_confidence(self, result: ExtractionResult) -> float:
        """Calculate average confidence across all fields."""
        if not result.fields:
            return 0.0
        
        total = sum(f.confidence for f in result.fields.values())
        return total / len(result.fields)
