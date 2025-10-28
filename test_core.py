"""
Test script for core functionality.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr_proofread.core.loader import FileLoader
from ocr_proofread.core.validator import Validator

# Test loading flat directory
print("Testing flat directory loading...")
flat_dir = "/home/runner/work/ocr-proofread/ocr-proofread/tests/sample-data/life-of"
session = FileLoader.load_files(flat_dir)
print(f"Loaded {session.total_units} units from flat directory")

for idx, unit in enumerate(session.units):
    print(f"\nUnit {idx}: {unit.image_filename}")
    print(f"  Basename: {unit.basename}")
    print(f"  hOCR files: {len(unit.hocr_documents)}")
    for doc in unit.hocr_documents:
        print(f"    - {doc.filename}")
    
    # Count words
    words = unit.primary_document.page.get_all_words()
    print(f"  Total words: {len(words)}")
    if words:
        print(f"  First word: {words[0]}")

# Test validation
print("\n\nTesting validation...")
validator = Validator()
messages = validator.validate_all_units(session.units)
print(f"Validation messages: {len(messages)}")
for msg in messages[:5]:  # Show first 5
    print(f"  {msg}")

# Test batch directory loading
print("\n\nTesting batch directory loading...")
batch_dir = "/home/runner/work/ocr-proofread/ocr-proofread/tests/sample-data/batches-life-of"
batch_session = FileLoader.load_files(batch_dir)
print(f"Loaded {batch_session.total_units} units from batch directory")

for idx, unit in enumerate(batch_session.units):
    print(f"\nUnit {idx}: {unit.image_filename}")
    print(f"  Subdirectory: {unit.subdirectory}")
    print(f"  hOCR files: {len(unit.hocr_documents)}")

print("\n\nCore functionality test completed successfully!")
