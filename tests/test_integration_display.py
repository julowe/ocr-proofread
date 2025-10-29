#!/usr/bin/env python3
"""
Manual integration test to verify the display name functionality.
"""

import sys
import os
import time
import subprocess
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_display_names():
    """Test that display names are correctly shown in the API."""
    print("=" * 60)
    print("Display Name Integration Test")
    print("=" * 60)
    
    # Use the sample data
    sample_dir = "tests/sample-data/life-of"
    
    print(f"\n1. Using sample data from: {sample_dir}")
    
    # Create a simple test by loading files directly
    from ocr_proofread.core.loader import FileLoader
    from ocr_proofread.core.models import ProofreadSession
    
    # Load the session
    session = FileLoader.load_files(sample_dir)
    print(f"   Loaded {session.total_units} units")
    
    # Get the first unit
    unit = session.units[0]
    print(f"\n2. First unit:")
    print(f"   Image: {unit.image_filename}")
    print(f"   Basename: {unit.basename}")
    print(f"   Number of hOCR documents: {len(unit.hocr_documents)}")
    
    # Check display names
    print(f"\n3. Checking display names:")
    for i, doc in enumerate(unit.hocr_documents):
        display_name = FileLoader.create_display_name(doc.filename, unit.basename)
        print(f"   Document {i+1}:")
        print(f"     Original filename: {doc.filename}")
        print(f"     Display name:      {display_name}")
        
        # Verify the display name is correct
        expected_parts = doc.filename.replace(unit.basename, "[...]")
        if display_name == expected_parts:
            print(f"     ✓ Display name is correct!")
        else:
            print(f"     ✗ ERROR: Expected '{expected_parts}'")
            return False
    
    print("\n" + "=" * 60)
    print("✅ All display names are correct!")
    print("=" * 60)
    return True


def test_web_api():
    """Test the web API returns display names correctly."""
    print("\n" + "=" * 60)
    print("Web API Display Name Test")
    print("=" * 60)
    
    try:
        # Check if server is running
        response = requests.get('http://127.0.0.1:5000/', timeout=2)
        print("✓ Web server is running")
    except requests.exceptions.ConnectionError:
        print("✗ Web server is not running")
        print("  Start the server with: python3 run_web.py")
        return False
    
    # Upload sample files
    sample_dir = "tests/sample-data/life-of"
    files = []
    
    try:
        for filename in os.listdir(sample_dir):
            filepath = os.path.join(sample_dir, filename)
            if os.path.isfile(filepath):
                files.append(('files', (filename, open(filepath, 'rb'))))
        
        print("\n1. Uploading sample files...")
        session = requests.Session()
        upload_response = session.post('http://127.0.0.1:5000/upload', files=files)
    finally:
        # Close file handles
        for _, (_, fh) in files:
            fh.close()
    
    if upload_response.status_code != 200:
        print(f"✗ Upload failed: {upload_response.status_code}")
        return False
    
    print("✓ Upload successful")
    
    # Get unit data
    print("\n2. Retrieving unit data from API...")
    unit_response = session.get('http://127.0.0.1:5000/api/unit/0')
    
    if unit_response.status_code != 200:
        print(f"✗ Failed to get unit data: {unit_response.status_code}")
        return False
    
    data = unit_response.json()
    print(f"✓ Retrieved unit data")
    print(f"  Image: {data['image_filename']}")
    
    # Check display names in the API response
    print("\n3. Checking display names in API response:")
    
    if not data['words'] or len(data['words']) == 0:
        print("✗ No words found in unit")
        return False
    
    first_word = data['words'][0]
    all_correct = True
    
    for i, text_data in enumerate(first_word['texts']):
        filename = text_data['filename']
        display_name = text_data.get('display_name', 'NOT FOUND')
        
        print(f"\n   Option {i+1}:")
        print(f"     Filename:     {filename}")
        print(f"     Display name: {display_name}")
        
        # Verify it contains [...]
        if '[...]' in display_name:
            print(f"     ✓ Display name contains [...] as expected")
        else:
            print(f"     ✗ ERROR: Display name should contain [...]")
            all_correct = False
        
        # Verify the pattern matches expected output
        if filename.endswith('-proofread.hocr') and display_name == '[...]-proofread.hocr':
            print(f"     ✓ Proofread file pattern correct")
        elif filename.endswith('.hocr') and not filename.endswith('-proofread.hocr') and display_name == '[...].hocr':
            print(f"     ✓ Basic hOCR file pattern correct")
    
    if all_correct:
        print("\n" + "=" * 60)
        print("✅ Web API display names are correct!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ Some display names are incorrect")
        print("=" * 60)
        return False


if __name__ == '__main__':
    # Test core functionality
    core_passed = test_display_names()
    
    # Test web API if available
    web_passed = test_web_api()
    
    if core_passed and web_passed:
        sys.exit(0)
    else:
        sys.exit(1)
