"""
Validation module for proofreading units.

Validates bounding boxes, image dimensions, and creates log messages.
"""

import logging
from typing import List, Tuple, Dict
from PIL import Image

from .models import ProofreadingUnit, HocrWord, BoundingBox
from .config import get_config


logger = logging.getLogger(__name__)


class ValidationMessage:
    """
    Represents a validation message.
    
    Attributes:
    level (str): Message level ('info', 'warning', 'critical').
    message (str): Message text.
    unit_index (int): Index of proofreading unit.
    """
    
    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_CRITICAL = 'critical'
    
    def __init__(self, level: str, message: str, unit_index: int = None):
        """
        Initialize validation message.
        
        Parameters:
        level (str): Message level.
        message (str): Message text.
        unit_index (int): Unit index, if applicable.
        """
        self.level = level
        self.message = message
        self.unit_index = unit_index
    
    def __str__(self) -> str:
        """Return string representation."""
        prefix = f"[{self.level.upper()}]"
        if self.unit_index is not None:
            prefix += f" [Unit {self.unit_index}]"
        return f"{prefix} {self.message}"


class Validator:
    """
    Validates proofreading units.
    
    Checks bounding boxes, image dimensions, and word matching.
    """
    
    def __init__(self):
        """Initialize validator."""
        self.config = get_config()
        self.messages: List[ValidationMessage] = []
    
    def validate_unit(self, unit: ProofreadingUnit, unit_index: int) -> List[ValidationMessage]:
        """
        Validate a proofreading unit.
        
        Parameters:
        unit (ProofreadingUnit): Unit to validate.
        unit_index (int): Index of unit.
        
        Returns:
        List[ValidationMessage]: List of validation messages.
        """
        messages = []
        
        # Validate image dimensions match page bbox
        messages.extend(self._validate_image_dimensions(unit, unit_index))
        
        # Validate bounding boxes across hOCR files
        if len(unit.hocr_documents) > 1:
            messages.extend(self._validate_bounding_boxes(unit, unit_index))
        
        return messages
    
    def _validate_image_dimensions(
        self, unit: ProofreadingUnit, unit_index: int
    ) -> List[ValidationMessage]:
        """
        Validate image dimensions match page bounding box.
        
        Parameters:
        unit (ProofreadingUnit): Unit to validate.
        unit_index (int): Index of unit.
        
        Returns:
        List[ValidationMessage]: List of validation messages.
        """
        messages = []
        
        try:
            # Load image to get dimensions
            with Image.open(unit.image_path) as img:
                img_width, img_height = img.size
            
            # Get page bbox dimensions
            page_bbox = unit.primary_document.page.bbox
            bbox_width = page_bbox.x2 - page_bbox.x1
            bbox_height = page_bbox.y2 - page_bbox.y1
            
            # Check if dimensions match
            if img_width != bbox_width or img_height != bbox_height:
                message = (
                    f"Image dimensions ({img_width}x{img_height}) do not match "
                    f"page bbox dimensions ({bbox_width}x{bbox_height}) "
                    f"for {unit.image_filename}"
                )
                messages.append(
                    ValidationMessage(ValidationMessage.LEVEL_CRITICAL, message, unit_index)
                )
                logger.critical(message)
        
        except Exception as e:
            message = f"Failed to validate image dimensions for {unit.image_filename}: {e}"
            messages.append(
                ValidationMessage(ValidationMessage.LEVEL_CRITICAL, message, unit_index)
            )
            logger.error(message)
        
        return messages
    
    def _validate_bounding_boxes(
        self, unit: ProofreadingUnit, unit_index: int
    ) -> List[ValidationMessage]:
        """
        Validate bounding boxes across multiple hOCR files.
        
        Parameters:
        unit (ProofreadingUnit): Unit to validate.
        unit_index (int): Index of unit.
        
        Returns:
        List[ValidationMessage]: List of validation messages.
        """
        messages = []
        
        # Get all words from primary document
        primary_words = unit.primary_document.page.get_all_words()
        
        # Build word lookup for other documents
        other_words_by_id: Dict[str, List[HocrWord]] = {}
        for doc in unit.hocr_documents[1:]:
            for word in doc.page.get_all_words():
                if word.word_id not in other_words_by_id:
                    other_words_by_id[word.word_id] = []
                other_words_by_id[word.word_id].append(word)
        
        # Compare bounding boxes
        tolerance = self.config.bbox_tolerance
        critical_threshold = self.config.bbox_critical_threshold
        
        for primary_word in primary_words:
            word_id = primary_word.word_id
            
            if word_id not in other_words_by_id:
                continue
            
            for other_word in other_words_by_id[word_id]:
                max_diff = primary_word.bbox.max_difference(other_word.bbox)
                
                if max_diff > critical_threshold:
                    message = (
                        f"Critical bounding box difference ({max_diff}px) "
                        f"for word '{word_id}' in {unit.image_filename} "
                        f"between {unit.primary_document.filename} and {other_word}"
                    )
                    messages.append(
                        ValidationMessage(ValidationMessage.LEVEL_CRITICAL, message, unit_index)
                    )
                    logger.critical(message)
                
                elif max_diff > tolerance:
                    message = (
                        f"Bounding box difference ({max_diff}px) "
                        f"for word '{word_id}' in {unit.image_filename}"
                    )
                    messages.append(
                        ValidationMessage(ValidationMessage.LEVEL_WARNING, message, unit_index)
                    )
                    logger.warning(message)
        
        return messages
    
    def validate_all_units(self, units: List[ProofreadingUnit]) -> List[ValidationMessage]:
        """
        Validate all proofreading units.
        
        Parameters:
        units (List[ProofreadingUnit]): List of units to validate.
        
        Returns:
        List[ValidationMessage]: List of all validation messages.
        """
        all_messages = []
        
        for idx, unit in enumerate(units):
            messages = self.validate_unit(unit, idx)
            all_messages.extend(messages)
        
        return all_messages
    
    @staticmethod
    def words_match_across_documents(unit: ProofreadingUnit, word_id: str) -> bool:
        """
        Check if a word's text matches across all hOCR documents.
        
        Parameters:
        unit (ProofreadingUnit): Proofreading unit.
        word_id (str): Word ID to check.
        
        Returns:
        bool: True if text matches across all documents.
        """
        texts = set()
        
        for doc in unit.hocr_documents:
            word = doc.get_word_by_id(word_id)
            if word:
                texts.add(word.text)
        
        return len(texts) <= 1
    
    @staticmethod
    def all_words_match_in_unit(unit: ProofreadingUnit) -> bool:
        """
        Check if all words match across all hOCR documents in a unit.
        
        Parameters:
        unit (ProofreadingUnit): Proofreading unit.
        
        Returns:
        bool: True if all words match.
        """
        if len(unit.hocr_documents) <= 1:
            return True
        
        # Get all word IDs from primary document
        primary_words = unit.primary_document.page.get_all_words()
        
        for word in primary_words:
            if not Validator.words_match_across_documents(unit, word.word_id):
                return False
        
        return True
