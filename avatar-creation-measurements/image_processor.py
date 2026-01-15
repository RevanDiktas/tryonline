"""
Image processing module for body measurement pipeline.

Handles image validation, preprocessing, and body detection
before SMPL reconstruction.
"""

import base64
import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image


class ImageFormat(Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"


@dataclass
class ImageValidationResult:
    """Result of image validation."""
    is_valid: bool
    error_message: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class ProcessedImage:
    """Container for processed image data."""
    image: np.ndarray
    original_size: Tuple[int, int]
    processed_size: Tuple[int, int]
    has_full_body: bool


class ImageProcessor:
    """
    Handles image validation and preprocessing for body measurement.

    Validates input images meet requirements for accurate body
    reconstruction (resolution, format, full-body visibility).
    """

    MIN_WIDTH = 256
    MIN_HEIGHT = 384
    MAX_WIDTH = 4096
    MAX_HEIGHT = 4096
    RECOMMENDED_WIDTH = 512
    RECOMMENDED_HEIGHT = 768
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, target_size: Tuple[int, int] = (512, 768)):
        """
        Initialize image processor.

        Args:
            target_size: Target (width, height) for preprocessing.
        """
        self.target_size = target_size

    def validate_image(
        self,
        image: Union[str, bytes, np.ndarray, Image.Image]
    ) -> ImageValidationResult:
        """
        Validate image meets requirements for body measurement.

        Args:
            image: Input image as path, base64 string, bytes,
                   numpy array, or PIL Image.

        Returns:
            ImageValidationResult with validation status and details.
        """
        try:
            img = self._load_image(image)
        except Exception as e:
            return ImageValidationResult(
                is_valid=False,
                error_message=f"Failed to load image: {str(e)}"
            )

        width, height = img.size

        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            return ImageValidationResult(
                is_valid=False,
                error_message=(
                    f"Image too small. Minimum size: "
                    f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}. "
                    f"Got: {width}x{height}"
                ),
                width=width,
                height=height
            )

        if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
            return ImageValidationResult(
                is_valid=False,
                error_message=(
                    f"Image too large. Maximum size: "
                    f"{self.MAX_WIDTH}x{self.MAX_HEIGHT}. "
                    f"Got: {width}x{height}"
                ),
                width=width,
                height=height
            )

        aspect_ratio = height / width
        if aspect_ratio < 1.0:
            return ImageValidationResult(
                is_valid=False,
                error_message=(
                    "Image should be portrait orientation (taller than wide) "
                    "for full-body capture."
                ),
                width=width,
                height=height
            )

        return ImageValidationResult(
            is_valid=True,
            width=width,
            height=height
        )

    def preprocess(
        self,
        image: Union[str, bytes, np.ndarray, Image.Image],
        detect_body: bool = True
    ) -> ProcessedImage:
        """
        Preprocess image for SMPL reconstruction.

        Args:
            image: Input image in various formats.
            detect_body: Whether to check for full body presence.

        Returns:
            ProcessedImage with normalized image ready for inference.

        Raises:
            ValueError: If image fails validation.
        """
        validation = self.validate_image(image)
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        img = self._load_image(image)
        original_size = img.size

        img_array = np.array(img)
        if len(img_array.shape) == 2:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
        elif img_array.shape[2] == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

        img_resized = self._resize_with_padding(
            img_array,
            self.target_size
        )

        has_full_body = True
        if detect_body:
            has_full_body = self._check_full_body(img_resized)

        return ProcessedImage(
            image=img_resized,
            original_size=original_size,
            processed_size=self.target_size,
            has_full_body=has_full_body
        )

    def _load_image(
        self,
        image: Union[str, bytes, np.ndarray, Image.Image]
    ) -> Image.Image:
        """
        Load image from various input formats.

        Args:
            image: Image as path, base64, bytes, numpy array, or PIL Image.

        Returns:
            PIL Image object.
        """
        if isinstance(image, Image.Image):
            return image.convert("RGB")

        if isinstance(image, np.ndarray):
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            return Image.fromarray(image).convert("RGB")

        if isinstance(image, str):
            if Path(image).exists():
                return Image.open(image).convert("RGB")

            try:
                if "," in image:
                    image = image.split(",")[1]
                image_bytes = base64.b64decode(image)
                return Image.open(io.BytesIO(image_bytes)).convert("RGB")
            except Exception:
                raise ValueError(
                    f"Invalid image string: not a valid path or base64 data"
                )

        if isinstance(image, bytes):
            return Image.open(io.BytesIO(image)).convert("RGB")

        raise ValueError(f"Unsupported image type: {type(image)}")

    def _resize_with_padding(
        self,
        image: np.ndarray,
        target_size: Tuple[int, int]
    ) -> np.ndarray:
        """
        Resize image to target size while maintaining aspect ratio.

        Uses padding to fill remaining space.

        Args:
            image: Input image as numpy array (H, W, C).
            target_size: Target (width, height).

        Returns:
            Resized and padded image.
        """
        target_w, target_h = target_size
        h, w = image.shape[:2]

        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(
            image,
            (new_w, new_h),
            interpolation=cv2.INTER_LINEAR
        )

        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)

        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2

        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    def _check_full_body(self, image: np.ndarray) -> bool:
        """
        Check if image likely contains a full body.

        Uses simple heuristics based on aspect ratio and coverage.
        Full detection would require a pose estimator.

        Args:
            image: Preprocessed image array.

        Returns:
            True if full body likely present.
        """
        h, w = image.shape[:2]

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        non_black = np.sum(gray > 10)
        total_pixels = h * w
        coverage = non_black / total_pixels

        if coverage < 0.1:
            return False

        return True

    def encode_base64(self, image: np.ndarray) -> str:
        """
        Encode numpy array image to base64 string.

        Args:
            image: Image as numpy array.

        Returns:
            Base64 encoded string.
        """
        img = Image.fromarray(image)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def decode_base64(self, base64_str: str) -> np.ndarray:
        """
        Decode base64 string to numpy array.

        Args:
            base64_str: Base64 encoded image string.

        Returns:
            Image as numpy array.
        """
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        image_bytes = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(image_bytes))
        return np.array(img.convert("RGB"))
