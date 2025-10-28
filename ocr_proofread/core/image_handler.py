"""
Image handler for OCR proofreading.

Handles loading images including JP2 format, with conversion if needed.
"""

import os
from typing import Tuple, Optional
from PIL import Image
import logging

from .config import get_config


logger = logging.getLogger(__name__)


class ImageHandler:
    """
    Handles image loading and conversion.
    
    Supports standard formats plus JP2 with automatic conversion.
    """
    
    def __init__(self):
        """Initialize image handler."""
        self.config = get_config()
        self._jp2_support = self._check_jp2_support()
    
    def _check_jp2_support(self) -> bool:
        """
        Check if Pillow has JP2 support.
        
        Returns:
        bool: True if JP2 is supported.
        """
        try:
            # Try to check for JPEG2000 support
            from PIL import Image
            return 'JPEG2000' in Image.EXTENSION
        except:
            return False
    
    def load_image(self, image_path: str) -> Image.Image:
        """
        Load an image file.
        
        For JP2 files, attempts to load directly or converts to PNG.
        
        Parameters:
        image_path (str): Path to image file.
        
        Returns:
        Image.Image: Loaded PIL Image object.
        
        Raises:
        FileNotFoundError: If image file does not exist.
        ValueError: If image cannot be loaded.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        ext = os.path.splitext(image_path)[1].lower()
        
        # Handle JP2 files
        if ext == '.jp2':
            return self._load_jp2(image_path)
        
        # Load standard image formats
        try:
            return Image.open(image_path)
        except Exception as e:
            raise ValueError(f"Failed to load image {image_path}: {e}")
    
    def _load_jp2(self, image_path: str) -> Image.Image:
        """
        Load a JP2 image file.
        
        Attempts direct loading with Pillow. If not supported, tries glymur.
        
        Parameters:
        image_path (str): Path to JP2 file.
        
        Returns:
        Image.Image: Loaded PIL Image object.
        
        Raises:
        ValueError: If JP2 cannot be loaded.
        """
        # First try direct Pillow loading
        try:
            img = Image.open(image_path)
            # Force load to check if it works
            img.load()
            logger.info(f"Loaded JP2 image directly: {image_path}")
            return img
        except Exception as e:
            logger.warning(f"Pillow JP2 loading failed: {e}, trying glymur")
        
        # Try glymur as fallback
        try:
            import glymur
            jp2 = glymur.Jp2k(image_path)
            array = jp2[:]
            img = Image.fromarray(array)
            logger.info(f"Loaded JP2 image with glymur: {image_path}")
            return img
        except ImportError:
            logger.warning("glymur not available for JP2 support")
        except Exception as e:
            logger.warning(f"glymur JP2 loading failed: {e}")
        
        raise ValueError(
            f"Cannot load JP2 file {image_path}. "
            "Install glymur or ensure Pillow has JPEG2000 support."
        )
    
    def get_image_size(self, image_path: str) -> Tuple[int, int]:
        """
        Get image dimensions without loading full image.
        
        Parameters:
        image_path (str): Path to image file.
        
        Returns:
        Tuple[int, int]: Width and height.
        """
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            logger.error(f"Failed to get image size for {image_path}: {e}")
            return (0, 0)
    
    def convert_jp2_to_png(
        self, jp2_path: str, output_path: str = None
    ) -> str:
        """
        Convert JP2 image to PNG.
        
        Parameters:
        jp2_path (str): Path to JP2 file.
        output_path (str): Output PNG path. If None, creates temporary file.
        
        Returns:
        str: Path to output PNG file.
        
        Raises:
        ValueError: If conversion fails.
        """
        if output_path is None:
            # Create output path with .png extension
            output_path = os.path.splitext(jp2_path)[0] + '_converted.png'
        
        try:
            img = self._load_jp2(jp2_path)
            
            # Get compression level from config
            compress_level = self.config.jp2_compression_level
            
            # Save as PNG with compression
            img.save(output_path, 'PNG', compress_level=compress_level)
            
            logger.info(f"Converted JP2 to PNG: {jp2_path} -> {output_path}")
            return output_path
        
        except Exception as e:
            raise ValueError(f"Failed to convert JP2 to PNG: {e}")
