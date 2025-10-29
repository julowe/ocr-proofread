#!/usr/bin/env python3
"""
Entry point for web OCR proofreading application.
"""

import os
from ocr_proofread.web.app import run_web_app

if __name__ == '__main__':
    # Allow host and port to be configured via environment variables
    # Default to 0.0.0.0 for Docker compatibility (can be accessed from outside container)
    # Use 127.0.0.1 for local development if HOST env var not set
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print("Starting OCR Proofreading Web Application...")
    print(f"Server will be accessible at: http://{host}:{port}")
    print("Press Ctrl+C to stop the server")
    run_web_app(host=host, port=port, debug=debug)
