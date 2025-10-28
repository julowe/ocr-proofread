"""
File loader for OCR proofreading.

Handles loading images and hOCR files from directories, correlating
them into proofreading units.
"""

import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

from .models import ProofreadingUnit, ProofreadSession
from .parser import HocrParser


logger = logging.getLogger(__name__)


class FileLoader:
    """
    Loads and correlates image and hOCR files.
    
    Supports both flat directory structure and subdirectory batches.
    """
    
    # Supported image extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.jp2'}
    HOCR_EXTENSION = '.hocr'
    
    @staticmethod
    def get_basename(filename: str) -> str:
        """
        Extract basename from filename.
        
        For files like 'page_001.jpg' or 'page_001.hocr', returns 'page_001'.
        For files like 'page_001-proofread.hocr', returns 'page_001'.
        
        Parameters:
        filename (str): Filename to process.
        
        Returns:
        str: Basename without extension.
        """
        # Remove extension
        name = os.path.splitext(filename)[0]
        
        # Remove common suffixes like '-proofread'
        for suffix in ['-proofread', '_proofread', '-ocr', '_ocr']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        return name
    
    @staticmethod
    def load_flat_directory(directory: str) -> List[ProofreadingUnit]:
        """
        Load files from a flat directory structure.
        
        Groups files by common basename (e.g., 'page_001.jpg' with 'page_001.hocr').
        
        Parameters:
        directory (str): Path to directory.
        
        Returns:
        List[ProofreadingUnit]: List of proofreading units.
        """
        units = []
        
        # Group files by basename
        files_by_basename: Dict[str, Dict[str, List[str]]] = {}
        
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if not os.path.isfile(filepath):
                continue
            
            ext = os.path.splitext(filename)[1].lower()
            
            if ext in FileLoader.IMAGE_EXTENSIONS:
                basename = FileLoader.get_basename(filename)
                if basename not in files_by_basename:
                    files_by_basename[basename] = {'images': [], 'hocr': []}
                files_by_basename[basename]['images'].append(filepath)
            
            elif ext == FileLoader.HOCR_EXTENSION:
                basename = FileLoader.get_basename(filename)
                if basename not in files_by_basename:
                    files_by_basename[basename] = {'images': [], 'hocr': []}
                files_by_basename[basename]['hocr'].append(filepath)
        
        # Create proofreading units
        for basename, files in sorted(files_by_basename.items()):
            if not files['images']:
                logger.warning(f"No image found for basename: {basename}")
                continue
            
            if not files['hocr']:
                logger.warning(f"No hOCR files found for basename: {basename}")
                continue
            
            # Use first image if multiple found
            image_path = files['images'][0]
            if len(files['images']) > 1:
                logger.warning(f"Multiple images for {basename}, using {image_path}")
            
            # Parse all hOCR files
            hocr_documents = []
            for hocr_path in files['hocr']:
                try:
                    doc = HocrParser.parse_file(hocr_path)
                    hocr_documents.append(doc)
                except Exception as e:
                    logger.error(f"Failed to parse {hocr_path}: {e}")
            
            if hocr_documents:
                unit = ProofreadingUnit(
                    image_path=image_path,
                    image_filename=os.path.basename(image_path),
                    hocr_documents=hocr_documents,
                    basename=basename,
                    subdirectory=None
                )
                units.append(unit)
        
        return units
    
    @staticmethod
    def load_subdirectory_batches(parent_directory: str) -> List[ProofreadingUnit]:
        """
        Load files from subdirectory batch structure.
        
        Each subdirectory should contain one image and one or more hOCR files.
        
        Parameters:
        parent_directory (str): Path to parent directory containing subdirectories.
        
        Returns:
        List[ProofreadingUnit]: List of proofreading units.
        """
        units = []
        
        # Process each subdirectory
        for subdir_name in sorted(os.listdir(parent_directory)):
            subdir_path = os.path.join(parent_directory, subdir_name)
            if not os.path.isdir(subdir_path):
                continue
            
            # Find image and hOCR files in this subdirectory
            image_files = []
            hocr_files = []
            
            for filename in os.listdir(subdir_path):
                filepath = os.path.join(subdir_path, filename)
                if not os.path.isfile(filepath):
                    continue
                
                ext = os.path.splitext(filename)[1].lower()
                
                if ext in FileLoader.IMAGE_EXTENSIONS:
                    image_files.append(filepath)
                elif ext == FileLoader.HOCR_EXTENSION:
                    hocr_files.append(filepath)
            
            if not image_files:
                logger.warning(f"No image found in subdirectory: {subdir_name}")
                continue
            
            if not hocr_files:
                logger.warning(f"No hOCR files found in subdirectory: {subdir_name}")
                continue
            
            # Use first image
            image_path = image_files[0]
            if len(image_files) > 1:
                logger.warning(f"Multiple images in {subdir_name}, using {image_path}")
            
            # Parse all hOCR files
            hocr_documents = []
            for hocr_path in hocr_files:
                try:
                    doc = HocrParser.parse_file(hocr_path)
                    hocr_documents.append(doc)
                except Exception as e:
                    logger.error(f"Failed to parse {hocr_path}: {e}")
            
            if hocr_documents:
                basename = FileLoader.get_basename(os.path.basename(image_path))
                unit = ProofreadingUnit(
                    image_path=image_path,
                    image_filename=os.path.basename(image_path),
                    hocr_documents=hocr_documents,
                    basename=basename,
                    subdirectory=subdir_name
                )
                units.append(unit)
        
        return units
    
    @staticmethod
    def detect_directory_structure(path: str) -> str:
        """
        Detect whether path is flat directory or contains subdirectories.
        
        Parameters:
        path (str): Directory path.
        
        Returns:
        str: 'flat' or 'batches'.
        """
        if not os.path.isdir(path):
            return 'flat'
        
        # Check if directory contains subdirectories with images
        subdirs_with_images = 0
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                # Check if this subdirectory contains images
                for subitem in os.listdir(item_path):
                    ext = os.path.splitext(subitem)[1].lower()
                    if ext in FileLoader.IMAGE_EXTENSIONS:
                        subdirs_with_images += 1
                        break
        
        # If we have subdirectories with images, it's a batch structure
        return 'batches' if subdirs_with_images > 0 else 'flat'
    
    @staticmethod
    def load_files(path: str) -> ProofreadSession:
        """
        Load files from a directory and create a proofreading session.
        
        Automatically detects flat or batch directory structure.
        
        Parameters:
        path (str): Path to directory or file selection.
        
        Returns:
        ProofreadSession: Proofreading session with all units.
        
        Raises:
        ValueError: If no valid proofreading units found.
        """
        if not os.path.exists(path):
            raise ValueError(f"Path does not exist: {path}")
        
        if os.path.isfile(path):
            # If a file was selected, use its directory
            path = os.path.dirname(path)
        
        structure = FileLoader.detect_directory_structure(path)
        logger.info(f"Detected {structure} directory structure")
        
        if structure == 'batches':
            units = FileLoader.load_subdirectory_batches(path)
        else:
            units = FileLoader.load_flat_directory(path)
        
        if not units:
            raise ValueError(f"No valid proofreading units found in {path}")
        
        logger.info(f"Loaded {len(units)} proofreading units")
        
        return ProofreadSession(units=units)
    
    @staticmethod
    def calculate_total_size(path: str) -> int:
        """
        Calculate total size of all files in directory.
        
        Parameters:
        path (str): Directory path.
        
        Returns:
        int: Total size in bytes.
        """
        total_size = 0
        
        for root, dirs, files in os.walk(path):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
        
        return total_size
