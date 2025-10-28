"""
hOCR file parser.

Parses hOCR XML files and extracts word-level data including text,
bounding boxes, and metadata.
"""

import os
from datetime import datetime
from typing import List, Optional
from lxml import etree
from lxml.etree import _Element

from .models import (
    BoundingBox, HocrWord, HocrLine, HocrPage, HocrDocument
)


class HocrParser:
    """
    Parser for hOCR files.
    
    Extracts word-level bounding boxes and text from hOCR XML files.
    """
    
    @staticmethod
    def parse_title_attribute(title: str) -> dict:
        """
        Parse hOCR title attribute into dictionary.
        
        Parameters:
        title (str): Title attribute value.
        
        Returns:
        dict: Parsed attributes.
        """
        result = {}
        parts = title.split(';')
        for part in parts:
            part = part.strip()
            if ' ' in part:
                key_value = part.split(None, 1)
                if len(key_value) == 2:
                    key, value = key_value
                    result[key] = value
        return result
    
    @staticmethod
    def extract_bbox(title_attrs: dict) -> Optional[BoundingBox]:
        """
        Extract bounding box from parsed title attributes.
        
        Parameters:
        title_attrs (dict): Parsed title attributes.
        
        Returns:
        BoundingBox: Extracted bounding box or None.
        """
        if 'bbox' not in title_attrs:
            return None
        
        try:
            return BoundingBox.from_string(f"bbox {title_attrs['bbox']}")
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def parse_word(element: _Element) -> Optional[HocrWord]:
        """
        Parse a word element from hOCR.
        
        Parameters:
        element (_Element): XML element with class 'ocrx_word'.
        
        Returns:
        HocrWord: Parsed word object or None if parsing fails.
        """
        word_id = element.get('id')
        if not word_id:
            return None
        
        title = element.get('title', '')
        title_attrs = HocrParser.parse_title_attribute(title)
        
        bbox = HocrParser.extract_bbox(title_attrs)
        if not bbox:
            return None
        
        # Get text content
        text = ''.join(element.itertext()).strip()
        
        # Extract confidence if available
        confidence = 100
        if 'x_wconf' in title_attrs:
            try:
                confidence = int(title_attrs['x_wconf'])
            except ValueError:
                pass
        
        # Extract font if available
        font = title_attrs.get('x_font')
        
        return HocrWord(
            word_id=word_id,
            text=text,
            bbox=bbox,
            confidence=confidence,
            font=font
        )
    
    @staticmethod
    def parse_line(element: _Element) -> Optional[HocrLine]:
        """
        Parse a line element from hOCR.
        
        Parameters:
        element (_Element): XML element with class 'ocr_line'.
        
        Returns:
        HocrLine: Parsed line object or None if parsing fails.
        """
        title = element.get('title', '')
        title_attrs = HocrParser.parse_title_attribute(title)
        
        bbox = HocrParser.extract_bbox(title_attrs)
        if not bbox:
            return None
        
        line = HocrLine(bbox=bbox)
        
        # Find all word elements in this line
        word_elements = element.xpath(".//*[@class='ocrx_word']")
        for word_elem in word_elements:
            word = HocrParser.parse_word(word_elem)
            if word:
                line.words.append(word)
        
        return line
    
    @staticmethod
    def parse_page(element: _Element) -> Optional[HocrPage]:
        """
        Parse a page element from hOCR.
        
        Parameters:
        element (_Element): XML element with class 'ocr_page'.
        
        Returns:
        HocrPage: Parsed page object or None if parsing fails.
        """
        title = element.get('title', '')
        title_attrs = HocrParser.parse_title_attribute(title)
        
        bbox = HocrParser.extract_bbox(title_attrs)
        if not bbox:
            return None
        
        page = HocrPage(bbox=bbox)
        
        # Find all line elements in this page
        line_elements = element.xpath(".//*[@class='ocr_line']")
        for line_elem in line_elements:
            line = HocrParser.parse_line(line_elem)
            if line:
                page.lines.append(line)
        
        return page
    
    @staticmethod
    def parse_file(filepath: str) -> HocrDocument:
        """
        Parse an hOCR file.
        
        Parameters:
        filepath (str): Path to hOCR file.
        
        Returns:
        HocrDocument: Parsed hOCR document.
        
        Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file cannot be parsed.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Get file modification time
        modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        # Parse XML
        try:
            tree = etree.parse(filepath)
            root = tree.getroot()
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid XML in {filepath}: {e}")
        
        # Extract head content
        head_elem = root.find('.//{http://www.w3.org/1999/xhtml}head')
        if head_elem is None:
            head_elem = root.find('.//head')
        
        head_content = ""
        if head_elem is not None:
            head_content = etree.tostring(head_elem, encoding='unicode', method='html')
        
        # Find page element
        page_elem = root.xpath("//*[@class='ocr_page']")
        if not page_elem:
            raise ValueError(f"No ocr_page element found in {filepath}")
        
        page = HocrParser.parse_page(page_elem[0])
        if not page:
            raise ValueError(f"Failed to parse page in {filepath}")
        
        filename = os.path.basename(filepath)
        
        return HocrDocument(
            filename=filename,
            filepath=filepath,
            head_content=head_content,
            page=page,
            modified_time=modified_time
        )
