#!/usr/bin/env python3
"""
Test for filename display transformation.

Tests that filenames are correctly transformed to display format
with basename replaced by [...].
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr_proofread.core.loader import FileLoader


def test_create_display_name():
    """
    Test the create_display_name function.
    
    Verifies that basenames are correctly replaced with [...] in filenames.
    """
    print("Testing create_display_name function...")
    
    test_cases = [
        # (hocr_filename, basename, expected_display_name)
        ("lifeofmuhammadtr0000ibnh_0223.hocr", "lifeofmuhammadtr0000ibnh_0223", "[...].hocr"),
        ("lifeofmuhammadtr0000ibnh_0223-proofread.hocr", "lifeofmuhammadtr0000ibnh_0223", "[...]-proofread.hocr"),
        ("page_001.hocr", "page_001", "[...].hocr"),
        ("page_001-ocr.hocr", "page_001", "[...]-ocr.hocr"),
        ("document_abc_proofread.hocr", "document_abc", "[...]_proofread.hocr"),
        ("test-file.hocr", "test-file", "[...].hocr"),
    ]
    
    all_passed = True
    
    for hocr_filename, basename, expected in test_cases:
        result = FileLoader.create_display_name(hocr_filename, basename)
        passed = result == expected
        
        status = "✓" if passed else "✗"
        print(f"{status} {hocr_filename} + '{basename}' -> '{result}' (expected: '{expected}')")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_get_basename():
    """
    Test the get_basename function.
    
    Verifies that basenames are correctly extracted from filenames.
    """
    print("\nTesting get_basename function...")
    
    test_cases = [
        # (filename, expected_basename)
        ("lifeofmuhammadtr0000ibnh_0223.jpg", "lifeofmuhammadtr0000ibnh_0223"),
        ("lifeofmuhammadtr0000ibnh_0223.hocr", "lifeofmuhammadtr0000ibnh_0223"),
        ("lifeofmuhammadtr0000ibnh_0223-proofread.hocr", "lifeofmuhammadtr0000ibnh_0223"),
        ("page_001.jpg", "page_001"),
        ("page_001-proofread.hocr", "page_001"),
        ("page_001_proofread.hocr", "page_001"),
        ("document-ocr.hocr", "document"),
        ("document_ocr.hocr", "document"),
    ]
    
    all_passed = True
    
    for filename, expected in test_cases:
        result = FileLoader.get_basename(filename)
        passed = result == expected
        
        status = "✓" if passed else "✗"
        print(f"{status} {filename} -> '{result}' (expected: '{expected}')")
        
        if not passed:
            all_passed = False
    
    return all_passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("Filename Display Transformation Tests")
    print("=" * 60)
    
    all_passed = True
    
    if not test_get_basename():
        all_passed = False
    
    if not test_create_display_name():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
