"""PDF document parsing and image extraction."""

import io
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image

from .loader import LoadedDocument


@dataclass
class PDFPage:
    """Represents a single PDF page."""
    
    page_number: int
    text: str
    image: Image.Image
    width: float
    height: float


class PDFParser:
    """Parse PDF documents and extract text/images."""
    
    def __init__(self, dpi: int = 200):
        """Initialize PDF parser.
        
        Args:
            dpi: Resolution for page rendering (higher = better OCR, slower).
        """
        self.dpi = dpi
        self.zoom = dpi / 72  # PDF default is 72 DPI
    
    def parse(self, document: LoadedDocument) -> list[PDFPage]:
        """Parse PDF and extract pages as text and images.
        
        Args:
            document: LoadedDocument containing PDF bytes.
            
        Returns:
            List of PDFPage objects.
        """
        pages = []
        
        # Open PDF from bytes
        pdf_doc = fitz.open(stream=document.content, filetype="pdf")
        
        try:
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Extract text
                text = page.get_text("text")
                
                # Render page to image
                matrix = fitz.Matrix(self.zoom, self.zoom)
                pixmap = page.get_pixmap(matrix=matrix)
                
                # Convert to PIL Image
                img_data = pixmap.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                pages.append(PDFPage(
                    page_number=page_num + 1,
                    text=text,
                    image=image,
                    width=page.rect.width,
                    height=page.rect.height,
                ))
        finally:
            pdf_doc.close()
        
        return pages
    
    def extract_embedded_images(self, document: LoadedDocument) -> list[Image.Image]:
        """Extract embedded images from PDF.
        
        Args:
            document: LoadedDocument containing PDF bytes.
            
        Returns:
            List of PIL Images.
        """
        images = []
        pdf_doc = fitz.open(stream=document.content, filetype="pdf")
        
        try:
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    try:
                        image = Image.open(io.BytesIO(image_bytes))
                        images.append(image)
                    except Exception:
                        # Skip invalid images
                        continue
        finally:
            pdf_doc.close()
        
        return images
    
    def get_metadata(self, document: LoadedDocument) -> dict:
        """Extract PDF metadata.
        
        Args:
            document: LoadedDocument containing PDF bytes.
            
        Returns:
            Dictionary of metadata.
        """
        pdf_doc = fitz.open(stream=document.content, filetype="pdf")
        
        try:
            metadata = pdf_doc.metadata or {}
            metadata["page_count"] = len(pdf_doc)
            return metadata
        finally:
            pdf_doc.close()
