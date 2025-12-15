"""Image document loading and validation."""

import io
from dataclasses import dataclass

from PIL import Image, ExifTags

from .loader import LoadedDocument


@dataclass
class ImageInfo:
    """Information about a loaded image."""
    
    image: Image.Image
    width: int
    height: int
    format: str
    mode: str
    has_exif: bool
    orientation: int


class ImageParser:
    """Parse and process image documents."""
    
    def __init__(self, max_dimension: int = 4096):
        """Initialize image parser.
        
        Args:
            max_dimension: Maximum width/height before resizing.
        """
        self.max_dimension = max_dimension
    
    def parse(self, document: LoadedDocument) -> ImageInfo:
        """Parse image document and extract information.
        
        Args:
            document: LoadedDocument containing image bytes.
            
        Returns:
            ImageInfo with processed image.
        """
        image = Image.open(io.BytesIO(document.content))
        
        # Handle EXIF orientation
        orientation = 1
        has_exif = False
        
        try:
            exif = image._getexif()
            if exif:
                has_exif = True
                for tag, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag, tag)
                    if tag_name == "Orientation":
                        orientation = value
                        break
        except (AttributeError, KeyError):
            pass
        
        # Apply orientation correction
        image = self._apply_orientation(image, orientation)
        
        # Convert to RGB if necessary (for OCR compatibility)
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        
        # Resize if too large
        image = self._resize_if_needed(image)
        
        return ImageInfo(
            image=image,
            width=image.width,
            height=image.height,
            format=image.format or "UNKNOWN",
            mode=image.mode,
            has_exif=has_exif,
            orientation=orientation,
        )
    
    def _apply_orientation(self, image: Image.Image, orientation: int) -> Image.Image:
        """Apply EXIF orientation correction.
        
        Args:
            image: PIL Image.
            orientation: EXIF orientation value (1-8).
            
        Returns:
            Corrected image.
        """
        if orientation == 2:
            return image.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            return image.rotate(180)
        elif orientation == 4:
            return image.transpose(Image.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            return image.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 6:
            return image.rotate(-90, expand=True)
        elif orientation == 7:
            return image.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 8:
            return image.rotate(90, expand=True)
        return image
    
    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds maximum dimension.
        
        Args:
            image: PIL Image.
            
        Returns:
            Resized image or original if within limits.
        """
        width, height = image.size
        
        if width <= self.max_dimension and height <= self.max_dimension:
            return image
        
        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = self.max_dimension
            new_height = int(height * (self.max_dimension / width))
        else:
            new_height = self.max_dimension
            new_width = int(width * (self.max_dimension / height))
        
        return image.resize((new_width, new_height), Image.LANCZOS)
