"""
Export module for saving proofread hOCR files.

Handles exporting individual pages, batches, and merged hOCR files.
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from lxml import etree
import logging

from .models import ProofreadSession, ProofreadingUnit, HocrDocument


logger = logging.getLogger(__name__)


class HocrExporter:
    """
    Exports proofread hOCR files.
    
    Supports individual file export, batch export, and merged file export.
    """
    
    @staticmethod
    def generate_timestamp() -> str:
        """
        Generate timestamp for filename.
        
        Returns:
        str: Timestamp in format YYYYMMDDTHHMM (ISO without seconds/colons).
        """
        return datetime.now().strftime('%Y%m%dT%H%M')
    
    @staticmethod
    def create_output_filename(original_filename: str) -> str:
        """
        Create output filename with timestamp.
        
        For 'page_001.hocr', creates 'page_001_YYYYMMDDTHHMM.hocr'.
        
        Parameters:
        original_filename (str): Original filename.
        
        Returns:
        str: Output filename with timestamp.
        """
        name, ext = os.path.splitext(original_filename)
        timestamp = HocrExporter.generate_timestamp()
        return f"{name}_{timestamp}{ext}"
    
    @staticmethod
    def update_word_text(
        doc: HocrDocument,
        word_id: str,
        new_text: str
    ) -> HocrDocument:
        """
        Create updated hOCR document with new word text.
        
        Parameters:
        doc (HocrDocument): Original document.
        word_id (str): Word ID to update.
        new_text (str): New text value.
        
        Returns:
        HocrDocument: Document with updated text (original unchanged).
        """
        # Parse the original file to get full XML tree
        tree = etree.parse(doc.filepath)
        root = tree.getroot()
        
        # Find word element and update text
        # Handle both XHTML namespace and no namespace
        word_elem = root.xpath(
            f"//*[@id='{word_id}']",
            namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'}
        )
        
        if word_elem:
            # Update text content
            word_elem[0].text = new_text
        
        return tree
    
    @staticmethod
    def export_unit(
        unit: ProofreadingUnit,
        changes: Dict[str, any],
        output_path: str = None
    ) -> str:
        """
        Export a single proofreading unit to hOCR file.
        
        Parameters:
        unit (ProofreadingUnit): Unit to export.
        changes (Dict[str, any]): Dictionary of word_id -> changes (str or dict).
        output_path (str): Output file path. If None, creates in same directory.
        
        Returns:
        str: Path to exported file.
        """
        # Start with primary (newest) document
        primary_doc = unit.primary_document
        
        # Parse the original file
        tree = etree.parse(primary_doc.filepath)
        root = tree.getroot()
        
        # Apply all changes
        for word_id, change in changes.items():
            # Find word element
            word_elem = root.xpath(f"//*[@id='{word_id}']")
            if not word_elem:
                continue
            
            elem = word_elem[0]
            
            # Handle both old string format and new dict format
            if isinstance(change, str):
                elem.text = change
            elif isinstance(change, dict):
                # Update text if specified
                if 'text' in change:
                    elem.text = change['text']
                
                # Update formatting
                style = elem.get('style', '')
                style_parts = [s.strip() for s in style.split(';') if s.strip()]
                
                # Remove existing formatting styles
                style_parts = [s for s in style_parts 
                              if not s.startswith('font-style:') 
                              and not s.startswith('font-weight:')]
                
                # Add new formatting
                if change.get('is_italic'):
                    style_parts.append('font-style:italic')
                if change.get('is_bold'):
                    style_parts.append('font-weight:bold')
                
                # Handle superscript
                if change.get('is_superscript'):
                    # Wrap text in <sup> tag
                    text = elem.text or ''
                    elem.text = ''
                    sup_elem = etree.SubElement(elem, 'sup')
                    sup_elem.text = text
                else:
                    # Remove any existing <sup> tags
                    for sup in elem.findall('.//sup'):
                        if sup.text:
                            # Move text to parent
                            if elem.text:
                                elem.text += sup.text
                            else:
                                elem.text = sup.text
                        elem.remove(sup)
                
                # Update style attribute
                if style_parts:
                    elem.set('style', ';'.join(style_parts))
                elif 'style' in elem.attrib:
                    del elem.attrib['style']
        
        # Determine output path
        if output_path is None:
            # Create in same directory as original
            output_filename = HocrExporter.create_output_filename(primary_doc.filename)
            
            if unit.subdirectory:
                # If in subdirectory structure, save there
                parent_dir = os.path.dirname(os.path.dirname(primary_doc.filepath))
                output_path = os.path.join(parent_dir, unit.subdirectory, output_filename)
            else:
                # Save in same directory
                output_dir = os.path.dirname(primary_doc.filepath)
                output_path = os.path.join(output_dir, output_filename)
        
        # Write file
        tree.write(
            output_path,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True,
            method='xml'
        )
        
        logger.info(f"Exported hOCR file: {output_path}")
        return output_path
    
    @staticmethod
    def export_changed_units(session: ProofreadSession, output_dir: str = None) -> List[str]:
        """
        Export all units with changes.
        
        Parameters:
        session (ProofreadSession): Proofreading session.
        output_dir (str): Output directory. If None, uses original locations.
        
        Returns:
        List[str]: List of exported file paths.
        """
        exported_files = []
        
        for unit_index, changes in session.changes.items():
            if not changes:
                continue
            
            unit = session.units[unit_index]
            
            # Determine output path
            output_path = None
            if output_dir:
                output_filename = HocrExporter.create_output_filename(
                    unit.primary_document.filename
                )
                if unit.subdirectory:
                    subdir_path = os.path.join(output_dir, unit.subdirectory)
                    os.makedirs(subdir_path, exist_ok=True)
                    output_path = os.path.join(subdir_path, output_filename)
                else:
                    output_path = os.path.join(output_dir, output_filename)
            
            # Export unit
            exported_path = HocrExporter.export_unit(unit, changes, output_path)
            exported_files.append(exported_path)
        
        logger.info(f"Exported {len(exported_files)} changed units")
        return exported_files
    
    @staticmethod
    def create_merged_filename(first_image_name: str) -> str:
        """
        Create merged hOCR filename from first image name.
        
        For 'page_0001.jpg', creates 'page-onepage.hocr'.
        Removes numbers before extension.
        
        Parameters:
        first_image_name (str): First image filename.
        
        Returns:
        str: Merged filename.
        """
        # Remove extension
        name = os.path.splitext(first_image_name)[0]
        
        # Remove trailing numbers (e.g., '0001', '_123', '-456')
        name = re.sub(r'[_-]?\d+$', '', name)
        
        # Add suffix
        return f"{name}-onepage.hocr"
    
    @staticmethod
    def export_merged(
        session: ProofreadSession,
        output_path: str = None
    ) -> str:
        """
        Export merged hOCR file containing all pages.
        
        Parameters:
        session (ProofreadSession): Proofreading session.
        output_path (str): Output file path. If None, prompts user.
        
        Returns:
        str: Path to exported merged file.
        """
        # Use head from newest file of first unit
        first_unit = session.units[0]
        head_tree = etree.parse(first_unit.primary_document.filepath)
        head_root = head_tree.getroot()
        
        # Get head element
        head_elem = head_root.find('.//{http://www.w3.org/1999/xhtml}head')
        if head_elem is None:
            head_elem = head_root.find('.//head')
        
        # Create new document
        html = etree.Element(
            'html',
            xmlns='http://www.w3.org/1999/xhtml',
            lang='en'
        )
        html.set('{http://www.w3.org/XML/1998/namespace}lang', 'en')
        
        # Add head
        if head_elem is not None:
            html.append(head_elem)
        
        # Create body
        body = etree.SubElement(html, 'body')
        
        # Add each page's body content
        for unit_index, unit in enumerate(session.units):
            # Get changes for this unit
            changes = session.changes.get(unit_index, {})
            
            # Parse primary document
            unit_tree = etree.parse(unit.primary_document.filepath)
            unit_root = unit_tree.getroot()
            
            # Apply changes
            for word_id, new_text in changes.items():
                word_elem = unit_root.xpath(f"//*[@id='{word_id}']")
                if word_elem:
                    word_elem[0].text = new_text
            
            # Get body content
            unit_body = unit_root.find('.//{http://www.w3.org/1999/xhtml}body')
            if unit_body is None:
                unit_body = unit_root.find('.//body')
            
            # Add all children of unit body to merged body
            if unit_body is not None:
                for child in unit_body:
                    body.append(child)
        
        # Determine output path if not provided
        if output_path is None:
            first_image = session.units[0].image_filename
            default_name = HocrExporter.create_merged_filename(first_image)
            # For web app, this would prompt user
            # For now, save in same directory as first image
            first_dir = os.path.dirname(session.units[0].image_path)
            output_path = os.path.join(first_dir, default_name)
        
        # Create tree and write
        tree = etree.ElementTree(html)
        tree.write(
            output_path,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True,
            method='xml',
            doctype='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
                    '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        )
        
        logger.info(f"Exported merged hOCR file: {output_path}")
        return output_path
