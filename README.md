# OCR Proofreading Application

A comprehensive application for proofreading, editing, and outputting hOCR formatted files created from OCR processes. Available as both a web application and a standalone GUI that can be compiled into executables for Linux, Windows, and macOS.

## Features

- **Dual Interface**: Available as both web app and desktop GUI
- **Image Support**: Handles JPG, PNG, TIFF, and JP2 image formats
- **hOCR Processing**: Parse and edit hOCR files with word-level precision
- **Interactive Editing**: Click on bounding boxes in images to select and edit words
- **Multi-File Comparison**: Compare OCR results from multiple sources
- **Visual Validation**: Highlights matching vs. unmatched words with color-coded bounding boxes
- **Flexible Organization**: Supports both flat directory and subdirectory batch structures
- **Export Options**: Save individual pages, batch changes, or merged documents
- **Validation**: Automatic checking of bounding box consistency and image dimensions

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Install Dependencies

```bash
pip install -r requirements.txt
```

The required packages are:
- Flask (web framework)
- Pillow (image processing)
- lxml (XML/HTML parsing)
- PyYAML (configuration)
- glymur (JP2 image support)
- PyQt6 (desktop GUI)
- pyinstaller (for building executables)

## Running the Application

### Web Application

Start the web server:

```bash
python3 run_web.py
```

Then open your browser and navigate to:
```
http://127.0.0.1:5000
```

The web app allows you to:
1. Upload directories of images and hOCR files
2. View and edit OCR text
3. Download proofread files individually or as a ZIP archive
4. Export merged hOCR documents

**Note**: The web app has a configurable size limit (default 700MB) for uploads. This can be adjusted in `config.yaml`.

### Desktop Application

Run the desktop GUI directly:

```bash
python3 run_desktop.py
```

The desktop application provides:
- File browser for selecting directories
- Full-featured GUI with image display and editing
- Direct file system access for saving changes
- Real-time validation and logging

## Building Executables

### Linux and macOS

```bash
./build_desktop.sh
```

The executable will be created in `dist/OCR-Proofread`.

### Windows

```batch
build_desktop.bat
```

The executable will be created in `dist\OCR-Proofread.exe`.

### Manual Build

You can also build manually using PyInstaller:

```bash
pyinstaller --name="OCR-Proofread" \
            --windowed \
            --onefile \
            --add-data="config.yaml:." \
            run_desktop.py
```

## Usage Guide

### File Organization

The application supports two directory structures:

**1. Flat Directory Structure**
```
my-documents/
  ├── page_001.jpg
  ├── page_001.hocr
  ├── page_001-proofread.hocr
  ├── page_002.jpg
  ├── page_002.hocr
  └── page_002-proofread.hocr
```

**2. Batch Subdirectory Structure**
```
my-batches/
  ├── batch_001/
  │   ├── image.jpg
  │   ├── ocr_result.hocr
  │   └── manual_correction.hocr
  └── batch_002/
      ├── image.jpg
      └── ocr_result.hocr
```

The application automatically detects which structure you're using.

### Proofreading Workflow

1. **Load Files**: Select or upload a directory containing images and hOCR files

2. **Navigate**: Use Previous/Next Page buttons to move between images

3. **Select Words**: 
   - Click on bounding boxes in the image to select words
   - Use Previous/Next Word buttons to navigate sequentially

4. **Edit Text**:
   - Choose from OCR results from different files (radio buttons)
   - Enter custom text in the edit box
   - System warns if text exceeds bounding box size

5. **Save Changes**:
   - Save Current Page: Export just the current page with changes
   - Save All Changed: Export all modified pages
   - Export Merged: Create single hOCR file containing all pages

### Options

- **Skip matching words**: Automatically skip words that match across all hOCR files
- **Skip matching pages**: Skip entire pages where all words match
- **Prompt to save**: Ask before leaving a page with unsaved changes
- **Color customization**: Change colors for matching vs. unmatched words

### Validation

The application automatically validates:
- Image dimensions match page bounding boxes
- Bounding box consistency across multiple hOCR files (2px tolerance)
- Critical errors logged for large discrepancies (>20px)

## Configuration

Edit `config.yaml` to customize:

```yaml
# Maximum upload size for web app (MB)
max_upload_size_mb: 700

# Bounding box colors (RGB)
colors:
  matching_boxes: [0, 255, 0]      # Green
  unverified_boxes: [255, 255, 0]  # Yellow

# Bounding box settings
bbox:
  line_width: 3
  selection_opacity: 0.15
  tolerance_pixels: 2
  critical_threshold_pixels: 20

# Image conversion settings
image:
  jp2_compression_level: 1
```

## Sample Data

Sample data is provided in `tests/sample-data/`:
- `life-of/`: Flat directory structure example
- `batches-life-of/`: Batch subdirectory structure example

These contain real hOCR files and images for testing.

## Technical Details

### Architecture

The application is organized into three main packages:

- **`ocr_proofread.core`**: Shared business logic
  - Configuration management
  - hOCR parsing and validation
  - File loading and organization
  - Image handling (including JP2 support)
  - Export functionality

- **`ocr_proofread.web`**: Flask-based web application
  - RESTful API for file operations
  - HTML/JavaScript interface
  - Session management

- **`ocr_proofread.desktop`**: PyQt6-based GUI application
  - Native desktop interface
  - Direct file system access
  - Advanced image display with clickable regions

### hOCR Format

The application works with hOCR files that contain word-level bounding boxes:

```xml
<span class='ocrx_word' id='word_223_7' 
      title='bbox 256 161 302 196; x_wconf 100; x_font Georgia'>
  chief
</span>
```

Key attributes:
- `id`: Unique identifier for matching across files
- `bbox`: Bounding box coordinates (x1, y1, x2, y2)
- `x_wconf`: OCR confidence score
- `x_font`: Font information

## Troubleshooting

### JP2 Images Not Loading

If JP2 images fail to load, install additional dependencies:

```bash
# For glymur (requires OpenJPEG)
# On Ubuntu/Debian:
sudo apt-get install libopenjp2-7

# On macOS:
brew install openjpeg

# On Windows:
# Download OpenJPEG from https://www.openjpeg.org/
```

### PyQt6 Import Errors

If you encounter PyQt6 import errors:

```bash
pip install --upgrade PyQt6
```

### Web App Upload Fails

Check file size limits:
1. Verify total size doesn't exceed configured limit
2. Check web server timeout settings
3. Ensure sufficient disk space in temp directory

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please ensure:
1. Code follows PEP 8 style guidelines
2. Functions include docstrings
3. Changes are tested with sample data
4. README is updated for new features

## Support

For issues, questions, or contributions, please use the GitHub issue tracker.
