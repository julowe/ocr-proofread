#!/usr/bin/env python3
"""
Simple smoke test to verify the application can run.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from ocr_proofread.core import config, models, parser, loader, validator, exporter, image_handler
        print("✓ Core modules imported")
    except Exception as e:
        print(f"✗ Failed to import core modules: {e}")
        return False
    
    try:
        from ocr_proofread.web import app
        print("✓ Web module imported")
    except Exception as e:
        print(f"✗ Failed to import web module: {e}")
        return False
    
    try:
        from ocr_proofread.desktop import main
        print("✓ Desktop module imported")
    except Exception as e:
        # Desktop module may fail in headless environments
        if 'libEGL' in str(e) or 'display' in str(e).lower() or 'DISPLAY' in str(e):
            print("⚠ Desktop module requires display (expected in CI/headless)")
            return True  # This is acceptable
        else:
            print(f"✗ Failed to import desktop module: {e}")
            return False
    
    return True


def test_core_functionality():
    """Test basic core functionality."""
    print("\nTesting core functionality...")
    
    try:
        from ocr_proofread.core.config import get_config
        config = get_config()
        assert config.max_upload_size_mb > 0
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False
    
    try:
        from ocr_proofread.core.loader import FileLoader
        # Test with sample data if available
        sample_path = "tests/sample-data/life-of"
        if os.path.exists(sample_path):
            session = FileLoader.load_files(sample_path)
            assert session.total_units > 0
            print(f"✓ File loading works ({session.total_units} units loaded)")
        else:
            print("⚠ Sample data not found, skipping file loading test")
    except Exception as e:
        print(f"✗ File loading test failed: {e}")
        return False
    
    return True


def test_web_app():
    """Test web app can be created."""
    print("\nTesting web app...")
    
    try:
        from ocr_proofread.web.app import app
        with app.test_client() as client:
            response = client.get('/')
            assert response.status_code == 200
            print("✓ Web app routes work")
    except Exception as e:
        print(f"✗ Web app test failed: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("OCR Proofreading Application - Smoke Tests")
    print("=" * 50)
    
    all_passed = True
    
    if not test_imports():
        all_passed = False
    
    if not test_core_functionality():
        all_passed = False
    
    if not test_web_app():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All tests passed!")
        print("=" * 50)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 50)
        return 1


if __name__ == '__main__':
    sys.exit(main())
