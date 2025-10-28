"""
Flask web application for OCR proofreading.

Web-based interface with file upload, image display with clickable bounding boxes,
and proofreading interface.
"""

import os
import io
import json
import tempfile
import shutil
import zipfile
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify, send_file,
    session, redirect, url_for
)
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw
import base64
import logging

from ocr_proofread.core.config import get_config
from ocr_proofread.core.loader import FileLoader
from ocr_proofread.core.validator import Validator
from ocr_proofread.core.models import ProofreadSession
from ocr_proofread.core.exporter import HocrExporter
from ocr_proofread.core.image_handler import ImageHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = get_config().max_upload_size_bytes
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix='ocr_proofread_')

# Store sessions in memory (in production, use database)
proofread_sessions = {}


@app.route('/')
def index():
    """Render main page."""
    config = get_config()
    return render_template(
        'index.html',
        max_size_mb=config.max_upload_size_mb
    )


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload."""
    try:
        # Get uploaded files
        files = request.files.getlist('files')
        
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        # Create temporary directory for this session
        session_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Save uploaded files
        total_size = 0
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(session_dir, filename)
                
                # Create subdirectories if needed
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                file.save(filepath)
                total_size += os.path.getsize(filepath)
        
        # Check size limit
        config = get_config()
        if total_size > config.max_upload_size_bytes:
            shutil.rmtree(session_dir)
            return jsonify({
                'error': f'Total file size exceeds {config.max_upload_size_mb} MB limit'
            }), 400
        
        # Load files into proofreading session
        proofread_session = FileLoader.load_files(session_dir)
        
        # Validate
        validator = Validator()
        messages = validator.validate_all_units(proofread_session.units)
        
        # Store session
        proofread_sessions[session_id] = {
            'session': proofread_session,
            'dir': session_dir,
            'messages': messages
        }
        
        # Store session ID in Flask session
        session['session_id'] = session_id
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_units': proofread_session.total_units,
            'messages': [str(msg) for msg in messages]
        })
    
    except Exception as e:
        logger.exception("Upload failed")
        return jsonify({'error': str(e)}), 500


@app.route('/api/unit/<int:unit_index>')
def get_unit(unit_index):
    """Get proofreading unit data."""
    session_id = session.get('session_id')
    if not session_id or session_id not in proofread_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    proofread_session = proofread_sessions[session_id]['session']
    
    if unit_index < 0 or unit_index >= proofread_session.total_units:
        return jsonify({'error': 'Invalid unit index'}), 400
    
    unit = proofread_session.units[unit_index]
    
    # Get all words
    words = unit.primary_document.page.get_all_words()
    
    # Determine which words match
    matching_word_ids = []
    for word in words:
        if Validator.words_match_across_documents(unit, word.word_id):
            matching_word_ids.append(word.word_id)
    
    # Get word data from all documents
    words_data = []
    for word in words:
        word_texts = []
        for doc in unit.hocr_documents:
            doc_word = doc.get_word_by_id(word.word_id)
            if doc_word:
                word_texts.append({
                    'filename': doc.filename,
                    'text': doc_word.text
                })
        
        # Get current text (with changes)
        current_text = proofread_session.get_word_text(word.word_id, unit_index)
        
        words_data.append({
            'word_id': word.word_id,
            'bbox': {
                'x1': word.bbox.x1,
                'y1': word.bbox.y1,
                'x2': word.bbox.x2,
                'y2': word.bbox.y2
            },
            'texts': word_texts,
            'current_text': current_text,
            'matches': word.word_id in matching_word_ids
        })
    
    return jsonify({
        'unit_index': unit_index,
        'total_units': proofread_session.total_units,
        'image_filename': unit.image_filename,
        'words': words_data,
        'has_changes': proofread_session.has_changes(unit_index)
    })


@app.route('/api/image/<int:unit_index>')
def get_image(unit_index):
    """Get image with bounding boxes drawn."""
    session_id = session.get('session_id')
    if not session_id or session_id not in proofread_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    proofread_session = proofread_sessions[session_id]['session']
    
    if unit_index < 0 or unit_index >= proofread_session.total_units:
        return jsonify({'error': 'Invalid unit index'}), 400
    
    unit = proofread_session.units[unit_index]
    
    # Load image
    img_handler = ImageHandler()
    pil_image = img_handler.load_image(unit.image_path)
    
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    # Draw bounding boxes
    draw = ImageDraw.Draw(pil_image, 'RGBA')
    config = get_config()
    line_width = config.bbox_line_width
    
    words = unit.primary_document.page.get_all_words()
    
    # Get selected word from request
    selected_word_id = request.args.get('selected')
    
    for word in words:
        # Determine if word matches across files
        matches = Validator.words_match_across_documents(unit, word.word_id)
        
        if matches:
            color = tuple(config.matching_color)
        else:
            color = tuple(config.unverified_color)
        
        # Draw box
        bbox = word.bbox
        draw.rectangle(
            [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
            outline=color,
            width=line_width
        )
        
        # Highlight selected word
        if word.word_id == selected_word_id:
            overlay_color = color + (int(255 * config.bbox_selection_opacity),)
            draw.rectangle(
                [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
                fill=overlay_color
            )
    
    # Convert to bytes
    img_io = io.BytesIO()
    pil_image.save(img_io, 'JPEG', quality=90)
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg')


@app.route('/api/update_word', methods=['POST'])
def update_word():
    """Update word text."""
    session_id = session.get('session_id')
    if not session_id or session_id not in proofread_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.json
    unit_index = data.get('unit_index')
    word_id = data.get('word_id')
    new_text = data.get('text')
    
    if unit_index is None or not word_id or new_text is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    proofread_session = proofread_sessions[session_id]['session']
    proofread_session.set_word_text(word_id, new_text, unit_index)
    
    return jsonify({'success': True})


@app.route('/api/export_current', methods=['POST'])
def export_current():
    """Export current page."""
    session_id = session.get('session_id')
    if not session_id or session_id not in proofread_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.json
    unit_index = data.get('unit_index')
    
    if unit_index is None:
        return jsonify({'error': 'Missing unit_index'}), 400
    
    proofread_session = proofread_sessions[session_id]['session']
    
    if not proofread_session.has_changes(unit_index):
        return jsonify({'error': 'No changes to save'}), 400
    
    # Export to temporary file
    unit = proofread_session.units[unit_index]
    changes = proofread_session.changes[unit_index]
    
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.hocr',
        dir=proofread_sessions[session_id]['dir']
    )
    temp_file.close()
    
    HocrExporter.export_unit(unit, changes, temp_file.name)
    
    filename = HocrExporter.create_output_filename(unit.primary_document.filename)
    
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=filename,
        mimetype='application/xml'
    )


@app.route('/api/export_all', methods=['POST'])
def export_all():
    """Export all changed pages as ZIP."""
    session_id = session.get('session_id')
    if not session_id or session_id not in proofread_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    proofread_session = proofread_sessions[session_id]['session']
    session_dir = proofread_sessions[session_id]['dir']
    
    # Create temporary directory for exports
    export_dir = os.path.join(session_dir, 'exports')
    os.makedirs(export_dir, exist_ok=True)
    
    # Export all changed units
    exported_files = HocrExporter.export_changed_units(proofread_session, export_dir)
    
    if not exported_files:
        return jsonify({'error': 'No changes to export'}), 400
    
    # Create ZIP file
    zip_path = os.path.join(session_dir, 'exported_pages.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filepath in exported_files:
            # Preserve directory structure relative to export_dir
            arcname = os.path.relpath(filepath, export_dir)
            zipf.write(filepath, arcname)
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name='proofread_pages.zip',
        mimetype='application/zip'
    )


@app.route('/api/export_merged', methods=['POST'])
def export_merged():
    """Export merged hOCR file."""
    session_id = session.get('session_id')
    if not session_id or session_id not in proofread_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    proofread_session = proofread_sessions[session_id]['session']
    session_dir = proofread_sessions[session_id]['dir']
    
    # Export to temporary file
    default_name = HocrExporter.create_merged_filename(
        proofread_session.units[0].image_filename
    )
    
    merged_path = os.path.join(session_dir, default_name)
    HocrExporter.export_merged(proofread_session, merged_path)
    
    return send_file(
        merged_path,
        as_attachment=True,
        download_name=default_name,
        mimetype='application/xml'
    )


@app.route('/viewer')
def viewer():
    """Render proofreading viewer."""
    session_id = session.get('session_id')
    if not session_id or session_id not in proofread_sessions:
        return redirect(url_for('index'))
    
    return render_template('viewer.html')


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    config = get_config()
    return jsonify({
        'error': f'File size exceeds maximum of {config.max_upload_size_mb} MB'
    }), 413


def run_web_app(host='127.0.0.1', port=5000, debug=False):
    """
    Run the Flask web application.
    
    Parameters:
    host (str): Host to bind to.
    port (int): Port to bind to.
    debug (bool): Enable debug mode.
    """
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web_app(debug=True)
