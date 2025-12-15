"""OCR engine abstraction with EasyOCR and Tesseract fallback."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np
from PIL import Image


@dataclass
class OCRWord:
    """A single detected word with position and confidence."""
    
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    

@dataclass
class OCRResult:
    """Result from OCR processing."""
    
    full_text: str
    words: list[OCRWord]
    confidence: float  # Average confidence
    language: str = "en"
    engine_used: str = "unknown"


@runtime_checkable
class OCREngine(Protocol):
    """Protocol for OCR engines."""
    
    def recognize(self, image: Image.Image) -> OCRResult:
        """Perform OCR on an image."""
        ...


class EasyOCREngine:
    """EasyOCR-based text recognition."""
    
    def __init__(self, languages: list[str] = None, gpu: bool = False):
        """Initialize EasyOCR reader.
        
        Args:
            languages: List of language codes (e.g., ['en', 'hi']).
            gpu: Whether to use GPU acceleration.
        """
        import easyocr
        
        self.languages = languages or ["en"]
        self.reader = easyocr.Reader(self.languages, gpu=gpu)
    
    def recognize(self, image: Image.Image) -> OCRResult:
        """Perform OCR using EasyOCR.
        
        Args:
            image: PIL Image to process.
            
        Returns:
            OCRResult with extracted text.
        """
        # Convert PIL to numpy array
        img_array = np.array(image)
        
        # Run EasyOCR
        results = self.reader.readtext(img_array)
        
        words = []
        total_confidence = 0
        
        for bbox, text, confidence in results:
            # Convert bbox from polygon to rectangle
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            x1, y1 = min(x_coords), min(y_coords)
            x2, y2 = max(x_coords), max(y_coords)
            
            words.append(OCRWord(
                text=text,
                confidence=confidence,
                bbox=(int(x1), int(y1), int(x2), int(y2)),
            ))
            total_confidence += confidence
        
        # Build full text preserving rough layout
        full_text = self._build_text_from_words(words)
        avg_confidence = total_confidence / len(words) if words else 0.0
        
        return OCRResult(
            full_text=full_text,
            words=words,
            confidence=avg_confidence,
            language=",".join(self.languages),
            engine_used="easyocr",
        )
    
    def _build_text_from_words(self, words: list[OCRWord]) -> str:
        """Build text string from words, attempting to preserve layout."""
        if not words:
            return ""
        
        # Sort by y-coordinate (top to bottom), then x (left to right)
        sorted_words = sorted(words, key=lambda w: (w.bbox[1], w.bbox[0]))
        
        lines = []
        current_line = []
        current_y = sorted_words[0].bbox[1] if sorted_words else 0
        line_height_threshold = 20  # Pixels between lines
        
        for word in sorted_words:
            if abs(word.bbox[1] - current_y) > line_height_threshold:
                # New line
                if current_line:
                    lines.append(" ".join(w.text for w in current_line))
                current_line = [word]
                current_y = word.bbox[1]
            else:
                current_line.append(word)
        
        if current_line:
            lines.append(" ".join(w.text for w in current_line))
        
        return "\n".join(lines)


class TesseractEngine:
    """Tesseract OCR fallback engine."""
    
    def __init__(self, language: str = "eng"):
        """Initialize Tesseract.
        
        Args:
            language: Tesseract language code.
        """
        import pytesseract
        
        self.language = language
        self.pytesseract = pytesseract
    
    def recognize(self, image: Image.Image) -> OCRResult:
        """Perform OCR using Tesseract.
        
        Args:
            image: PIL Image to process.
            
        Returns:
            OCRResult with extracted text.
        """
        # Get detailed word-level data
        data = self.pytesseract.image_to_data(
            image, 
            lang=self.language,
            output_type=self.pytesseract.Output.DICT
        )
        
        words = []
        total_confidence = 0
        valid_word_count = 0
        
        for i, text in enumerate(data["text"]):
            if text.strip():
                conf = float(data["conf"][i])
                if conf > 0:  # Tesseract uses -1 for invalid
                    words.append(OCRWord(
                        text=text,
                        confidence=conf / 100,  # Normalize to 0-1
                        bbox=(
                            data["left"][i],
                            data["top"][i],
                            data["left"][i] + data["width"][i],
                            data["top"][i] + data["height"][i],
                        ),
                    ))
                    total_confidence += conf / 100
                    valid_word_count += 1
        
        # Get full text
        full_text = self.pytesseract.image_to_string(image, lang=self.language)
        avg_confidence = total_confidence / valid_word_count if valid_word_count else 0.0
        
        return OCRResult(
            full_text=full_text.strip(),
            words=words,
            confidence=avg_confidence,
            language=self.language,
            engine_used="tesseract",
        )


class OCRPipeline:
    """OCR pipeline with fallback support."""
    
    def __init__(
        self,
        primary_engine: OCREngine | None = None,
        fallback_engine: OCREngine | None = None,
        confidence_threshold: float = 0.5,
    ):
        """Initialize OCR pipeline.
        
        Args:
            primary_engine: Primary OCR engine (default: EasyOCR).
            fallback_engine: Fallback engine if primary fails (default: Tesseract if available).
            confidence_threshold: Minimum confidence before fallback.
        """
        self.primary_engine = primary_engine
        self.fallback_engine = fallback_engine
        self.confidence_threshold = confidence_threshold
        
        # Lazy initialization
        self._primary_initialized = False
        self._fallback_initialized = False
        self._fallback_available = True  # Track if fallback can be used
    
    def _ensure_primary(self):
        """Lazy initialize primary engine."""
        if not self._primary_initialized:
            if self.primary_engine is None:
                self.primary_engine = EasyOCREngine()
            self._primary_initialized = True
    
    def _ensure_fallback(self):
        """Lazy initialize fallback engine (optional)."""
        if not self._fallback_initialized:
            if self.fallback_engine is None:
                try:
                    self.fallback_engine = TesseractEngine()
                except Exception:
                    # Tesseract not installed - that's OK, we'll use primary only
                    self._fallback_available = False
            self._fallback_initialized = True
    
    def process(self, image: Image.Image) -> OCRResult:
        """Process image through OCR pipeline.
        
        Args:
            image: PIL Image to process.
            
        Returns:
            OCRResult from best performing engine.
        """
        # Try primary engine (EasyOCR)
        self._ensure_primary()
        try:
            result = self.primary_engine.recognize(image)
            
            if result.confidence >= self.confidence_threshold:
                return result
            
            # Low confidence, try fallback if available
            self._ensure_fallback()
            if self._fallback_available and self.fallback_engine:
                try:
                    fallback_result = self.fallback_engine.recognize(image)
                    # Return whichever has higher confidence
                    if fallback_result.confidence > result.confidence:
                        return fallback_result
                except Exception:
                    pass  # Fallback failed, use primary result
            
            return result
            
        except Exception as e:
            # Primary failed, try fallback
            self._ensure_fallback()
            if self._fallback_available and self.fallback_engine:
                try:
                    return self.fallback_engine.recognize(image)
                except Exception as fallback_error:
                    raise RuntimeError(
                        f"Both OCR engines failed. Primary: {e}, Fallback: {fallback_error}"
                    )
            raise RuntimeError(f"OCR failed: {e}")

