#!/usr/bin/env python3
"""
Entry point for web OCR proofreading application.
"""

from ocr_proofread.web.app import run_web_app

if __name__ == '__main__':
    print("Starting OCR Proofreading Web Application...")
    print("Open your browser and navigate to: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    run_web_app(host='127.0.0.1', port=5000, debug=False)
