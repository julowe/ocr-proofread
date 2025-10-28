"""
Data models for hOCR files and proofreading units.

Contains classes representing hOCR documents, words, bounding boxes,
and proofreading units.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from datetime import datetime


@dataclass
class BoundingBox:
    """
    Represents a bounding box with coordinates.
    
    Attributes:
    x1 (int): Left x coordinate.
    y1 (int): Top y coordinate.
    x2 (int): Right x coordinate.
    y2 (int): Bottom y coordinate.
    """
    x1: int
    y1: int
    x2: int
    y2: int
    
    def __str__(self) -> str:
        """Return string representation of bounding box."""
        return f"bbox {self.x1} {self.y1} {self.x2} {self.y2}"
    
    def matches(self, other: 'BoundingBox', tolerance: int = 2) -> bool:
        """
        Check if this bounding box matches another within tolerance.
        
        Parameters:
        other (BoundingBox): Other bounding box to compare.
        tolerance (int): Maximum pixel difference allowed.
        
        Returns:
        bool: True if boxes match within tolerance.
        """
        return (abs(self.x1 - other.x1) <= tolerance and
                abs(self.y1 - other.y1) <= tolerance and
                abs(self.x2 - other.x2) <= tolerance and
                abs(self.y2 - other.y2) <= tolerance)
    
    def max_difference(self, other: 'BoundingBox') -> int:
        """
        Calculate maximum pixel difference with another bounding box.
        
        Parameters:
        other (BoundingBox): Other bounding box to compare.
        
        Returns:
        int: Maximum pixel difference.
        """
        return max(
            abs(self.x1 - other.x1),
            abs(self.y1 - other.y1),
            abs(self.x2 - other.x2),
            abs(self.y2 - other.y2)
        )
    
    @classmethod
    def from_string(cls, bbox_str: str) -> 'BoundingBox':
        """
        Create BoundingBox from string like 'bbox 256 161 302 196'.
        
        Parameters:
        bbox_str (str): Bounding box string.
        
        Returns:
        BoundingBox: Parsed bounding box.
        """
        parts = bbox_str.strip().split()
        if len(parts) >= 5 and parts[0] == 'bbox':
            return cls(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
        raise ValueError(f"Invalid bbox string: {bbox_str}")


@dataclass
class HocrWord:
    """
    Represents a word in an hOCR file.
    
    Attributes:
    word_id (str): Unique identifier for the word (e.g., 'word_223_0').
    text (str): Text content of the word.
    bbox (BoundingBox): Bounding box coordinates.
    confidence (int): OCR confidence score.
    font (str): Font name if available.
    """
    word_id: str
    text: str
    bbox: BoundingBox
    confidence: int = 100
    font: Optional[str] = None
    
    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.word_id}: '{self.text}' @ {self.bbox}"


@dataclass
class HocrLine:
    """
    Represents a line in an hOCR file.
    
    Attributes:
    bbox (BoundingBox): Bounding box for the entire line.
    words (List[HocrWord]): List of words in the line.
    """
    bbox: BoundingBox
    words: List[HocrWord] = field(default_factory=list)


@dataclass
class HocrPage:
    """
    Represents a page in an hOCR file.
    
    Attributes:
    bbox (BoundingBox): Page bounding box.
    lines (List[HocrLine]): List of lines on the page.
    """
    bbox: BoundingBox
    lines: List[HocrLine] = field(default_factory=list)
    
    def get_all_words(self) -> List[HocrWord]:
        """
        Get all words from all lines on the page.
        
        Returns:
        List[HocrWord]: List of all words.
        """
        words = []
        for line in self.lines:
            words.extend(line.words)
        return words


@dataclass
class HocrDocument:
    """
    Represents a complete hOCR document.
    
    Attributes:
    filename (str): Name of the hOCR file.
    filepath (str): Full path to the file.
    head_content (str): Content of <head> element.
    page (HocrPage): Page data.
    modified_time (datetime): Last modification time of file.
    """
    filename: str
    filepath: str
    head_content: str
    page: HocrPage
    modified_time: datetime
    
    def get_word_by_id(self, word_id: str) -> Optional[HocrWord]:
        """
        Get a word by its ID.
        
        Parameters:
        word_id (str): Word ID to search for.
        
        Returns:
        HocrWord: Word object if found, None otherwise.
        """
        for word in self.page.get_all_words():
            if word.word_id == word_id:
                return word
        return None


@dataclass
class ProofreadingUnit:
    """
    Represents a proofreading unit (one image with one or more hOCR files).
    
    Attributes:
    image_path (str): Path to the image file.
    image_filename (str): Image filename.
    hocr_documents (List[HocrDocument]): List of hOCR documents for this image.
    basename (str): Common basename for files.
    subdirectory (str): Subdirectory path if organized in batches.
    """
    image_path: str
    image_filename: str
    hocr_documents: List[HocrDocument]
    basename: str
    subdirectory: Optional[str] = None
    
    def __post_init__(self):
        """Sort hOCR documents by modification time (newest first)."""
        self.hocr_documents.sort(key=lambda doc: doc.modified_time, reverse=True)
    
    @property
    def primary_document(self) -> HocrDocument:
        """
        Get the primary (newest) hOCR document.
        
        Returns:
        HocrDocument: Newest hOCR document.
        """
        return self.hocr_documents[0]
    
    def get_image_dimensions(self) -> Tuple[int, int]:
        """
        Get image dimensions from page bounding box.
        
        Returns:
        Tuple[int, int]: Width and height.
        """
        bbox = self.primary_document.page.bbox
        return (bbox.x2 - bbox.x1, bbox.y2 - bbox.y1)


@dataclass
class ProofreadSession:
    """
    Represents a complete proofreading session with all units.
    
    Attributes:
    units (List[ProofreadingUnit]): List of all proofreading units.
    current_index (int): Index of currently displayed unit.
    changes (Dict[int, Dict[str, str]]): Dictionary tracking changes per unit.
        Format: {unit_index: {word_id: new_text}}
    """
    units: List[ProofreadingUnit]
    current_index: int = 0
    changes: Dict[int, Dict[str, str]] = field(default_factory=dict)
    
    @property
    def current_unit(self) -> ProofreadingUnit:
        """
        Get current proofreading unit.
        
        Returns:
        ProofreadingUnit: Current unit being proofread.
        """
        return self.units[self.current_index]
    
    @property
    def total_units(self) -> int:
        """
        Get total number of units.
        
        Returns:
        int: Total unit count.
        """
        return len(self.units)
    
    def has_changes(self, unit_index: int = None) -> bool:
        """
        Check if a unit has changes.
        
        Parameters:
        unit_index (int): Unit index to check. If None, uses current unit.
        
        Returns:
        bool: True if unit has changes.
        """
        if unit_index is None:
            unit_index = self.current_index
        return unit_index in self.changes and len(self.changes[unit_index]) > 0
    
    def set_word_text(self, word_id: str, text: str, unit_index: int = None):
        """
        Set text for a word in a unit.
        
        Parameters:
        word_id (str): Word ID.
        text (str): New text value.
        unit_index (int): Unit index. If None, uses current unit.
        """
        if unit_index is None:
            unit_index = self.current_index
        
        if unit_index not in self.changes:
            self.changes[unit_index] = {}
        
        self.changes[unit_index][word_id] = text
    
    def get_word_text(self, word_id: str, unit_index: int = None) -> str:
        """
        Get current text for a word, including any changes.
        
        Parameters:
        word_id (str): Word ID.
        unit_index (int): Unit index. If None, uses current unit.
        
        Returns:
        str: Current text value.
        """
        if unit_index is None:
            unit_index = self.current_index
        
        # Check if there's a change recorded
        if unit_index in self.changes and word_id in self.changes[unit_index]:
            return self.changes[unit_index][word_id]
        
        # Otherwise return original text from primary document
        unit = self.units[unit_index]
        word = unit.primary_document.get_word_by_id(word_id)
        return word.text if word else ""
