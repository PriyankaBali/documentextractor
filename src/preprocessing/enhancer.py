"""Image enhancement for OCR preprocessing."""

import cv2
import numpy as np
from PIL import Image


class ImageEnhancer:
    """Enhance images for better OCR accuracy."""
    
    def __init__(
        self,
        denoise_strength: int = 10,
        sharpen_strength: float = 1.5,
        contrast_clip_limit: float = 2.0,
    ):
        """Initialize enhancer with parameters.
        
        Args:
            denoise_strength: Strength of denoising (0-30).
            sharpen_strength: Sharpening multiplier.
            contrast_clip_limit: CLAHE clip limit for contrast.
        """
        self.denoise_strength = denoise_strength
        self.sharpen_strength = sharpen_strength
        self.contrast_clip_limit = contrast_clip_limit
    
    def enhance(self, image: Image.Image) -> Image.Image:
        """Apply full enhancement pipeline.
        
        Args:
            image: PIL Image to enhance.
            
        Returns:
            Enhanced PIL Image.
        """
        # Convert PIL to OpenCV format
        cv_image = self._pil_to_cv(image)
        
        # Apply enhancements
        cv_image = self.denoise(cv_image)
        cv_image = self.enhance_contrast(cv_image)
        cv_image = self.sharpen(cv_image)
        cv_image = self.deskew(cv_image)
        
        # Convert back to PIL
        return self._cv_to_pil(cv_image)
    
    def denoise(self, cv_image: np.ndarray) -> np.ndarray:
        """Remove noise from image.
        
        Args:
            cv_image: OpenCV image array.
            
        Returns:
            Denoised image.
        """
        if len(cv_image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(
                cv_image, 
                None, 
                self.denoise_strength, 
                self.denoise_strength, 
                7, 
                21
            )
        else:
            return cv2.fastNlMeansDenoising(
                cv_image, 
                None, 
                self.denoise_strength, 
                7, 
                21
            )
    
    def enhance_contrast(self, cv_image: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE.
        
        Args:
            cv_image: OpenCV image array.
            
        Returns:
            Contrast-enhanced image.
        """
        # Convert to LAB color space
        if len(cv_image.shape) == 3:
            lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
        else:
            l_channel = cv_image
        
        # Apply CLAHE to luminance channel
        clahe = cv2.createCLAHE(
            clipLimit=self.contrast_clip_limit, 
            tileGridSize=(8, 8)
        )
        enhanced_l = clahe.apply(l_channel)
        
        # Merge back
        if len(cv_image.shape) == 3:
            enhanced_lab = cv2.merge([enhanced_l, a, b])
            return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        else:
            return enhanced_l
    
    def sharpen(self, cv_image: np.ndarray) -> np.ndarray:
        """Sharpen image to improve text edges.
        
        Args:
            cv_image: OpenCV image array.
            
        Returns:
            Sharpened image.
        """
        # Create sharpening kernel
        kernel = np.array([
            [0, -1, 0],
            [-1, 5 * self.sharpen_strength, -1],
            [0, -1, 0]
        ]) / self.sharpen_strength
        
        return cv2.filter2D(cv_image, -1, kernel)
    
    def deskew(self, cv_image: np.ndarray) -> np.ndarray:
        """Correct image rotation/skew.
        
        Args:
            cv_image: OpenCV image array.
            
        Returns:
            Deskewed image.
        """
        # Convert to grayscale for angle detection
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(
            edges, 
            1, 
            np.pi / 180, 
            threshold=100, 
            minLineLength=100, 
            maxLineGap=10
        )
        
        if lines is None or len(lines) == 0:
            return cv_image
        
        # Calculate average angle
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if abs(angle) < 45:  # Only consider near-horizontal lines
                    angles.append(angle)
        
        if not angles:
            return cv_image
        
        avg_angle = np.median(angles)
        
        # Only correct if angle is significant
        if abs(avg_angle) < 0.5:
            return cv_image
        
        # Rotate image
        height, width = cv_image.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
        
        return cv2.warpAffine(
            cv_image, 
            rotation_matrix, 
            (width, height),
            borderMode=cv2.BORDER_REPLICATE
        )
    
    def binarize(self, cv_image: np.ndarray) -> np.ndarray:
        """Convert to binary (black/white) for OCR.
        
        Args:
            cv_image: OpenCV image array.
            
        Returns:
            Binary image.
        """
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image
        
        # Adaptive thresholding
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
    
    def _pil_to_cv(self, pil_image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format."""
        if pil_image.mode == "RGB":
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        elif pil_image.mode == "L":
            return np.array(pil_image)
        else:
            rgb = pil_image.convert("RGB")
            return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    
    def _cv_to_pil(self, cv_image: np.ndarray) -> Image.Image:
        """Convert OpenCV image to PIL format."""
        if len(cv_image.shape) == 3:
            return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        else:
            return Image.fromarray(cv_image)
